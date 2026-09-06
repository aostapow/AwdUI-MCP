using System.Text.Json;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.UIA3;

namespace AwdUiUiaSidecar;

static class Program
{
    static int Main()
    {
        try
        {
            var line = Console.In.ReadLine();
            if (string.IsNullOrEmpty(line))
            {
                WriteError("empty request");
                return 1;
            }
            var req = JsonSerializer.Deserialize<Request>(line, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
            });
            if (req == null || string.IsNullOrEmpty(req.Command))
            {
                WriteError("invalid request");
                return 1;
            }
            var resp = Dispatch(req);
            Console.Out.WriteLine(JsonSerializer.Serialize(resp));
            return 0;
        }
        catch (Exception ex)
        {
            WriteError(ex.Message);
            return 1;
        }
    }

    static void WriteError(string msg) =>
        Console.Out.WriteLine(JsonSerializer.Serialize(new { error = msg }));

    static object Dispatch(Request req)
    {
        using var automation = new UIA3Automation();
        return req.Command switch
        {
            "from_point" => FromPoint(automation, req.Params),
            "find" => Find(automation, req.Params),
            "list_tree" => ListTree(automation, req.Params),
            "get_properties" => GetProperties(automation, req.Params),
            "invoke" => Invoke(automation, req.Params),
            "set_value" => SetValue(automation, req.Params),
            _ => new { error = $"unknown command: {req.Command}" },
        };
    }

    static AutomationElement? ResolveWindow(UIA3Automation automation, string title, JsonElement p)
    {
        if (p.TryGetProperty("hwnd", out var hwndProp))
        {
            var hwnd = hwndProp.GetInt64();
            if (hwnd > 0)
            {
                try { return automation.FromHandle((nint)hwnd); }
                catch { /* fall through */ }
            }
        }

        var desktop = automation.GetDesktop();
        if (string.IsNullOrEmpty(title))
        {
            var fg = automation.FocusedElement();
            if (fg != null) return fg;
            return desktop.FindFirstDescendant(cf => cf.ByControlType(ControlType.Window));
        }

        var windows = desktop.FindAllDescendants(cf => cf.ByControlType(ControlType.Window));
        AutomationElement? best = null;
        var bestScore = int.MinValue;
        var titleLower = title.ToLowerInvariant();
        foreach (var w in windows)
        {
            var name = w.Name ?? "";
            if (!name.Contains(title, StringComparison.OrdinalIgnoreCase))
                continue;
            var r = w.BoundingRectangle;
            var score = 0;
            if (name.Equals(title, StringComparison.OrdinalIgnoreCase)) score += 10000;
            if (r.X > -1000 && r.Y > -1000) score += 500;
            score += (int)(r.Width * r.Height) / 1000;
            var cls = (w.ClassName ?? "").ToLowerInvariant();
            if (titleLower is "calculadora" or "calculator")
            {
                if (cls.Contains("corewindow")) score += 8000;
            }
            if (cls.Contains("applicationframe")) score += 100;
            if (score > bestScore)
            {
                bestScore = score;
                best = w;
            }
        }
        return best;
    }

    static bool TryGetVisualRect(JsonElement p, out System.Drawing.Rectangle rect)
    {
        if (!p.TryGetProperty("window_rect", out var wr))
        {
            rect = default;
            return false;
        }
        if (!wr.TryGetProperty("x", out var xp) || !wr.TryGetProperty("y", out var yp))
        {
            rect = default;
            return false;
        }
        int w = wr.TryGetProperty("w", out var wp) ? wp.GetInt32()
            : wr.TryGetProperty("width", out var wp2) ? wp2.GetInt32() : 0;
        int h = wr.TryGetProperty("h", out var hp) ? hp.GetInt32()
            : wr.TryGetProperty("height", out var hp2) ? hp2.GetInt32() : 0;
        if (w <= 0 || h <= 0)
        {
            rect = default;
            return false;
        }
        rect = new System.Drawing.Rectangle(xp.GetInt32(), yp.GetInt32(), w, h);
        return true;
    }

    static bool ElementInScope(AutomationElement e, AutomationElement window, JsonElement p)
    {
        try
        {
            var er = e.BoundingRectangle;
            if (er.Width <= 0 && er.Height <= 0) return false;
            if (TryGetVisualRect(p, out var vr))
            {
                var cx = er.X + er.Width / 2.0;
                var cy = er.Y + er.Height / 2.0;
                return cx >= vr.Left && cx < vr.Right && cy >= vr.Top && cy < vr.Bottom;
            }
            return ElementInWindow(e, window);
        }
        catch { return false; }
    }

    static bool ElementInWindow(AutomationElement e, AutomationElement window)
    {
        try
        {
            var wr = window.BoundingRectangle;
            var er = e.BoundingRectangle;
            if (wr.Width <= 0 || wr.Height <= 0) return false;
            return wr.IntersectsWith(er);
        }
        catch { return false; }
    }

    static IEnumerable<AutomationElement> DesktopElementsInScope(
        UIA3Automation automation,
        AutomationElement window,
        JsonElement p)
    {
        foreach (var e in automation.GetDesktop().FindAllDescendants())
        {
            if (ElementInScope(e, window, p))
                yield return e;
        }
    }

    static IEnumerable<AutomationElement> DesktopElementsInWindow(
        UIA3Automation automation,
        AutomationElement window)
    {
        foreach (var e in automation.GetDesktop().FindAllDescendants())
        {
            if (ElementInWindow(e, window))
                yield return e;
        }
    }

    static string SafeString(Func<string> getter)
    {
        try { return getter(); }
        catch { return ""; }
    }

    static Dictionary<string, object?> ElemToDict(AutomationElement e)
    {
        var r = e.BoundingRectangle;
        var patterns = new List<string>();
        if (e.Patterns.Invoke.IsSupported) patterns.Add("Invoke");
        if (e.Patterns.Value.IsSupported) patterns.Add("Value");
        if (e.Patterns.Toggle.IsSupported) patterns.Add("Toggle");
        if (e.Patterns.ExpandCollapse.IsSupported) patterns.Add("ExpandCollapse");
        if (e.Patterns.Scroll.IsSupported) patterns.Add("Scroll");
        if (e.Patterns.LegacyIAccessible.IsSupported) patterns.Add("LegacyIAccessible");

        return new Dictionary<string, object?>
        {
            ["name"] = e.Name ?? "",
            ["role"] = e.ControlType.ToString(),
            ["x"] = (int)r.X,
            ["y"] = (int)r.Y,
            ["width"] = (int)r.Width,
            ["height"] = (int)r.Height,
            ["value"] = e.Properties.Name.ValueOrDefault ?? "",
            ["automation_id"] = e.AutomationId ?? "",
            ["class_name"] = e.ClassName ?? "",
            ["framework_id"] = e.Properties.FrameworkId.ValueOrDefault ?? "",
            ["enabled"] = e.IsEnabled,
            ["visible"] = !e.IsOffscreen,
            ["patterns"] = patterns,
        };
    }

    static object FromPoint(UIA3Automation automation, JsonElement p)
    {
        int x = p.GetProperty("x").GetInt32();
        int y = p.GetProperty("y").GetInt32();
        var elem = automation.FromPoint(new System.Drawing.Point(x, y));
        if (elem == null) return new { error = "no element" };
        return new { element = ElemToDict(elem) };
    }

    static object Find(UIA3Automation automation, JsonElement p)
    {
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { elements = Array.Empty<object>() };
        var name = GetStr(p, "name");
        var role = GetStr(p, "role");
        var aid = GetStr(p, "automation_id");
        var matches = new List<Dictionary<string, object?>>();

        void addIfMatch(AutomationElement e)
        {
            if (!string.IsNullOrEmpty(name) && !(e.Name ?? "").Contains(name, StringComparison.OrdinalIgnoreCase))
                return;
            if (!string.IsNullOrEmpty(role) && !e.ControlType.ToString().Equals(role, StringComparison.OrdinalIgnoreCase))
                return;
            if (!string.IsNullOrEmpty(aid) && (e.AutomationId ?? "") != aid)
                return;
            matches.Add(ElemToDict(e));
        }

        try
        {
            foreach (var e in window.FindAllDescendants())
                addIfMatch(e);
        }
        catch { /* fall through */ }

        if (matches.Count == 0)
        {
            try
            {
                foreach (var e in DesktopElementsInScope(automation, window, p))
                    addIfMatch(e);
            }
            catch { /* optional */ }
        }

        if (matches.Count == 0)
        {
            try
            {
                foreach (var e in DesktopElementsInWindow(automation, window))
                    addIfMatch(e);
            }
            catch { /* optional */ }
        }

        int index = p.TryGetProperty("index", out var ip) ? ip.GetInt32() : 0;
        if (index > 0 && matches.Count > index)
            matches = new List<Dictionary<string, object?>> { matches[index] };
        return new { elements = matches };
    }

    static object ListTree(UIA3Automation automation, JsonElement p)
    {
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { elements = Array.Empty<object>() };
        int maxDepth = p.TryGetProperty("max_depth", out var dp) ? dp.GetInt32() : 5;
        var role = GetStr(p, "role");
        var elements = new List<Dictionary<string, object?>>();

        void collectFrom(AutomationElement root)
        {
            try
            {
                foreach (var e in root.FindAllDescendants())
                {
                    if (elements.Count >= 500) break;
                    if (!string.IsNullOrEmpty(role) &&
                        !e.ControlType.ToString().Equals(role, StringComparison.OrdinalIgnoreCase))
                        continue;
                    var aid = e.AutomationId ?? "";
                    var ename = e.Name ?? "";
                    if (string.IsNullOrEmpty(aid) && string.IsNullOrEmpty(ename) &&
                        e.ControlType == ControlType.Pane)
                        continue;
                    elements.Add(ElemToDict(e));
                }
            }
            catch { /* skip */ }
        }

        collectFrom(window);
        SupplementDesktopInScope(automation, window, p, role, elements);
        return new { elements };
    }

    static void SupplementDesktopInScope(
        UIA3Automation automation,
        AutomationElement window,
        JsonElement p,
        string role,
        List<Dictionary<string, object?>> elements)
    {
        var seen = new HashSet<string>();
        foreach (var existing in elements)
        {
            seen.Add($"{existing.GetValueOrDefault("automation_id")}|{existing.GetValueOrDefault("x")}|{existing.GetValueOrDefault("y")}");
        }
        try
        {
            foreach (var e in DesktopElementsInScope(automation, window, p))
            {
                if (elements.Count >= 500) break;
                if (!string.IsNullOrEmpty(role) &&
                    !e.ControlType.ToString().Equals(role, StringComparison.OrdinalIgnoreCase))
                    continue;
                var aid = e.AutomationId ?? "";
                var ename = e.Name ?? "";
                if (string.IsNullOrEmpty(aid) && string.IsNullOrEmpty(ename) &&
                    e.ControlType == ControlType.Pane)
                    continue;
                var dict = ElemToDict(e);
                var key = $"{dict.GetValueOrDefault("automation_id")}|{dict.GetValueOrDefault("x")}|{dict.GetValueOrDefault("y")}";
                if (seen.Contains(key)) continue;
                elements.Add(dict);
                seen.Add(key);
            }
        }
        catch { /* optional */ }
    }

    static object GetProperties(UIA3Automation automation, JsonElement p)
    {
        var result = Find(automation, p);
        var json = JsonSerializer.Serialize(result);
        using var doc = JsonDocument.Parse(json);
        var elements = doc.RootElement.GetProperty("elements");
        if (elements.GetArrayLength() == 0)
            return new { error = "not found" };
        return new { properties = JsonSerializer.Deserialize<object>(elements[0].GetRawText()) };
    }

    static object Invoke(UIA3Automation automation, JsonElement p)
    {
        var result = Find(automation, p);
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { success = false, error = "no window" };
        var name = GetStr(p, "name");
        var elem = window.FindFirstDescendant(cf => cf.ByName(name));
        if (elem == null) return new { success = false, error = "not found" };
        elem.Patterns.Invoke.Pattern.Invoke();
        return new { success = true };
    }

    static object SetValue(UIA3Automation automation, JsonElement p)
    {
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { success = false, error = "no window" };
        var name = GetStr(p, "name");
        var value = GetStr(p, "value");
        var elem = window.FindFirstDescendant(cf => cf.ByName(name));
        if (elem == null) return new { success = false, error = "not found" };
        elem.Patterns.Value.Pattern.SetValue(value);
        return new { success = true };
    }

    static string GetStr(JsonElement p, string key) =>
        p.TryGetProperty(key, out var v) ? v.GetString() ?? "" : "";
}

class Request
{
    public string Command { get; set; } = "";
    public JsonElement Params { get; set; }
}
