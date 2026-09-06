using System.Collections.Concurrent;
using System.Text.Json;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.Core.EventHandlers;
using FlaUI.Core.Identifiers;
using FlaUI.UIA3;

namespace AwdUiEventSidecar;

static class Program
{
    [STAThread]
    static int Main(string[] args)
    {
        if (args.Any(a => a.Equals("--server", StringComparison.OrdinalIgnoreCase)))
            return RunServer();
        return RunSingleShot();
    }

    static int RunSingleShot()
    {
        try
        {
            var line = Console.In.ReadLine();
            if (string.IsNullOrEmpty(line))
            {
                WriteResponse(new { error = "empty request" });
                return 1;
            }
            var req = JsonSerializer.Deserialize<Request>(line, JsonOpts());
            if (req == null || string.IsNullOrEmpty(req.Command))
            {
                WriteResponse(new { error = "invalid request" });
                return 1;
            }
            WriteResponse(EventMonitorHost.Dispatch(req));
            return 0;
        }
        catch (Exception ex)
        {
            WriteResponse(new { error = ex.Message });
            return 1;
        }
    }

    static int RunServer()
    {
        try
        {
            string? line;
            while ((line = Console.In.ReadLine()) != null)
            {
                if (string.IsNullOrWhiteSpace(line))
                    continue;
                try
                {
                    var req = JsonSerializer.Deserialize<Request>(line, JsonOpts());
                    if (req == null || string.IsNullOrEmpty(req.Command))
                    {
                        WriteResponse(new { error = "invalid request" });
                        continue;
                    }
                    var resp = EventMonitorHost.Dispatch(req);
                    if (req.Id.HasValue)
                        resp = MergeId(resp, req.Id.Value);
                    WriteResponse(resp);
                }
                catch (Exception ex)
                {
                    WriteResponse(new { error = ex.Message });
                }
            }
            EventMonitorHost.ShutdownAll();
            return 0;
        }
        catch (Exception ex)
        {
            WriteResponse(new { error = ex.Message });
            return 1;
        }
    }

    static object MergeId(object resp, int id)
    {
        if (resp is Dictionary<string, object?> dict)
        {
            dict["id"] = id;
            return dict;
        }
        var json = JsonSerializer.Serialize(resp);
        using var doc = JsonDocument.Parse(json);
        var merged = new Dictionary<string, object?>();
        foreach (var prop in doc.RootElement.EnumerateObject())
            merged[prop.Name] = JsonSerializer.Deserialize<object>(prop.Value.GetRawText());
        merged["id"] = id;
        return merged;
    }

    static void WriteResponse(object resp)
    {
        Console.Out.WriteLine(JsonSerializer.Serialize(resp));
        Console.Out.Flush();
    }

    static JsonSerializerOptions JsonOpts() => new()
    {
        PropertyNameCaseInsensitive = true,
    };
}

sealed class Request
{
    public int? Id { get; set; }
    public string Command { get; set; } = "";
    public JsonElement Params { get; set; }
}

static class EventMonitorHost
{
    static readonly UIA3Automation Automation = new();
    static readonly ConcurrentDictionary<string, MonitorSession> Sessions = new();
    static readonly object FocusLock = new();
    static FocusChangedEventHandlerBase? _focusHandler;
    static readonly ConcurrentDictionary<string, byte> FocusSessionIds = new();

    public static object Dispatch(Request req) => req.Command switch
    {
        "monitor_start" => MonitorStart(req.Params),
        "monitor_get_events" => MonitorGetEvents(req.Params),
        "monitor_stop" => MonitorStop(req.Params),
        "monitor_stop_all" => MonitorStopAll(),
        "ping" => new { success = true, backend = "flaui_native" },
        _ => new { error = $"unknown command: {req.Command}" },
    };

    public static void ShutdownAll() => MonitorStopAll();

    static object MonitorStart(JsonElement p)
    {
        var sessionId = GetStr(p, "session_id");
        if (string.IsNullOrWhiteSpace(sessionId))
            sessionId = Guid.NewGuid().ToString("N")[..12];

        var eventType = (GetStr(p, "event_type") ?? "focus").ToLowerInvariant();
        var window = ResolveWindow(GetStr(p, "window_title"), p);
        if (window == null)
            return new { success = false, error = "window not found" };

        AutomationElement scope = window;
        var scopeAid = GetStr(p, "automation_id");
        var scopeName = GetStr(p, "name");
        if (!string.IsNullOrEmpty(scopeAid))
        {
            var byId = window.FindFirstDescendant(cf => cf.ByAutomationId(scopeAid));
            if (byId != null) scope = byId;
        }
        else if (!string.IsNullOrEmpty(scopeName))
        {
            var byName = window.FindFirstDescendant(cf => cf.ByName(scopeName));
            if (byName != null) scope = byName;
        }

        if (Sessions.ContainsKey(sessionId))
            MonitorStopSession(sessionId);

        var session = new MonitorSession
        {
            SessionId = sessionId,
            EventType = eventType,
            Window = window,
            Scope = scope,
            Events = new ConcurrentQueue<Dictionary<string, object?>>(),
        };

        try
        {
            if (eventType is "focus" or "focuschanged")
                RegisterFocus(session);
            else if (eventType is "structurechanged" or "structure")
                RegisterStructure(session);
            else if (eventType is "propertychanged" or "property")
                RegisterProperty(session);
            else
                return new { success = false, error = $"unsupported event_type: {eventType}" };
        }
        catch (Exception ex)
        {
            return new { success = false, error = ex.Message };
        }

        Sessions[sessionId] = session;
        return new
        {
            success = true,
            session_id = sessionId,
            event_type = eventType,
            backend = "flaui_native",
        };
    }

    static void RegisterFocus(MonitorSession session)
    {
        FocusSessionIds[session.SessionId] = 1;
        lock (FocusLock)
        {
            if (_focusHandler == null)
            {
                _focusHandler = Automation.RegisterFocusChangedEvent(element =>
                {
                    foreach (var sid in FocusSessionIds.Keys)
                    {
                        if (!Sessions.TryGetValue(sid, out var s)) continue;
                        if (!InWindow(element, s.Window)) continue;
                        s.Events.Enqueue(MakeEvent("focus", element));
                        TrimQueue(s.Events);
                    }
                });
            }
        }
        session.Unregister = () =>
        {
            FocusSessionIds.TryRemove(session.SessionId, out _);
            if (FocusSessionIds.IsEmpty && _focusHandler != null)
            {
                lock (FocusLock)
                {
                    if (FocusSessionIds.IsEmpty && _focusHandler != null)
                    {
                        try { Automation.UnregisterFocusChangedEvent(_focusHandler); }
                        catch { /* ignore */ }
                        _focusHandler = null;
                    }
                }
            }
        };
    }

    static void RegisterStructure(MonitorSession session)
    {
        var handler = session.Scope.RegisterStructureChangedEvent(TreeScope.Subtree, (_, changeType, _) =>
        {
            session.Events.Enqueue(new Dictionary<string, object?>
            {
                ["type"] = "structurechanged",
                ["timestamp"] = Now(),
                ["change_type"] = changeType.ToString(),
                ["scope_automation_id"] = session.Scope.AutomationId ?? "",
            });
            TrimQueue(session.Events);
        });
        session.StructureHandler = handler;
        session.Unregister = () =>
        {
            try { session.Scope.FrameworkAutomationElement.UnregisterStructureChangedEventHandler(handler); }
            catch { /* ignore */ }
        };
    }

    static void RegisterProperty(MonitorSession session)
    {
        var elProps = Automation.PropertyLibrary.Element;
        var valueProp = Automation.PropertyLibrary.Value.Value;
        var handler = session.Scope.RegisterPropertyChangedEvent(
            TreeScope.Subtree,
            (_, propertyId, newValue) =>
            {
                session.Events.Enqueue(new Dictionary<string, object?>
                {
                    ["type"] = "propertychanged",
                    ["timestamp"] = Now(),
                    ["property_id"] = propertyId.ToString(),
                    ["value"] = newValue?.ToString() ?? "",
                    ["scope_automation_id"] = session.Scope.AutomationId ?? "",
                });
                TrimQueue(session.Events);
            },
            elProps.Name,
            elProps.AutomationId,
            valueProp);
        session.PropertyHandler = handler;
        session.Unregister = () =>
        {
            try { session.Scope.FrameworkAutomationElement.UnregisterPropertyChangedEventHandler(handler); }
            catch { /* ignore */ }
        };
    }

    static object MonitorGetEvents(JsonElement p)
    {
        var sessionId = GetStr(p, "session_id");
        if (string.IsNullOrEmpty(sessionId) || !Sessions.TryGetValue(sessionId, out var session))
            return new { success = false, error = $"unknown session: {sessionId}" };

        int maxCount = p.TryGetProperty("max_count", out var mc) ? mc.GetInt32() : 100;
        maxCount = Math.Clamp(maxCount, 1, 500);
        var events = new List<Dictionary<string, object?>>();
        while (events.Count < maxCount && session.Events.TryDequeue(out var ev))
            events.Add(ev);

        return new
        {
            success = true,
            session_id = sessionId,
            count = events.Count,
            events,
            backend = "flaui_native",
        };
    }

    static object MonitorStop(JsonElement p)
    {
        var sessionId = GetStr(p, "session_id");
        if (string.IsNullOrEmpty(sessionId))
            return new { success = false, error = "session_id required" };
        var stopped = MonitorStopSession(sessionId);
        return new { success = stopped, session_id = sessionId, stopped };
    }

    static object MonitorStopAll()
    {
        var ids = Sessions.Keys.ToList();
        foreach (var id in ids)
            MonitorStopSession(id);
        return new { success = true, stopped = ids.Count, sessions = ids };
    }

    static bool MonitorStopSession(string sessionId)
    {
        if (!Sessions.TryRemove(sessionId, out var session))
            return false;
        try { session.Unregister?.Invoke(); }
        catch { /* ignore */ }
        return true;
    }

    static bool InWindow(AutomationElement element, AutomationElement window)
    {
        try
        {
            var wr = window.BoundingRectangle;
            var er = element.BoundingRectangle;
            if (wr.Width <= 0 || wr.Height <= 0) return false;
            return wr.IntersectsWith(er);
        }
        catch { return false; }
    }

    static Dictionary<string, object?> MakeEvent(string type, AutomationElement element)
    {
        var r = element.BoundingRectangle;
        return new Dictionary<string, object?>
        {
            ["type"] = type,
            ["timestamp"] = Now(),
            ["detail"] = new Dictionary<string, object?>
            {
                ["name"] = element.Name ?? "",
                ["automation_id"] = element.AutomationId ?? "",
                ["role"] = element.ControlType.ToString(),
                ["x"] = (int)r.X,
                ["y"] = (int)r.Y,
                ["width"] = (int)r.Width,
                ["height"] = (int)r.Height,
            },
        };
    }

    static double Now() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;

    static void TrimQueue(ConcurrentQueue<Dictionary<string, object?>> queue)
    {
        while (queue.Count > 500 && queue.TryDequeue(out _)) { }
    }

    static AutomationElement? ResolveWindow(string title, JsonElement p)
    {
        if (p.TryGetProperty("hwnd", out var hwndProp))
        {
            var hwnd = hwndProp.GetInt64();
            if (hwnd > 0)
            {
                try { return Automation.FromHandle((nint)hwnd); }
                catch { /* fall through */ }
            }
        }

        var desktop = Automation.GetDesktop();
        if (string.IsNullOrEmpty(title))
        {
            return Automation.FocusedElement() ?? desktop.FindFirstDescendant(cf => cf.ByControlType(ControlType.Window));
        }

        AutomationElement? best = null;
        var bestScore = int.MinValue;
        foreach (var w in desktop.FindAllDescendants(cf => cf.ByControlType(ControlType.Window)))
        {
            var name = w.Name ?? "";
            if (!name.Contains(title, StringComparison.OrdinalIgnoreCase))
                continue;
            var r = w.BoundingRectangle;
            var score = (int)(r.Width * r.Height) / 1000;
            if (name.Equals(title, StringComparison.OrdinalIgnoreCase)) score += 10000;
            if (score > bestScore)
            {
                bestScore = score;
                best = w;
            }
        }
        return best;
    }

    static string GetStr(JsonElement p, string key) =>
        p.TryGetProperty(key, out var v) ? v.GetString() ?? "" : "";
}

sealed class MonitorSession
{
    public required string SessionId { get; init; }
    public required string EventType { get; init; }
    public required AutomationElement Window { get; init; }
    public required AutomationElement Scope { get; init; }
    public required ConcurrentQueue<Dictionary<string, object?>> Events { get; init; }
    public Action? Unregister { get; set; }
    public StructureChangedEventHandlerBase? StructureHandler { get; set; }
    public PropertyChangedEventHandlerBase? PropertyHandler { get; set; }
}
