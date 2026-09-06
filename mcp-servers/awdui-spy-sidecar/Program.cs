using System.Text.Json;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.UIA3;

namespace AwdUiSpySidecar;

static class Program
{
    [STAThread]
    static int Main()
    {
        Application.EnableVisualStyles();
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

    static object Dispatch(Request req) => req.Command switch
    {
        "from_point" => FromPoint(req.Params),
        "inspect_full" => InspectFull(req.Params),
        "walk_tree" => WalkTree(req.Params),
        "invoke" => InvokeCmd(req.Params),
        "expand_collapse" => ExpandCollapseCmd(req.Params),
        "highlight" => HighlightCmd(req.Params),
        "unhighlight" => HighlightOverlay.Unhighlight(),
        _ => new { error = $"unknown command: {req.Command}" },
    };

    static object HighlightCmd(JsonElement p)
    {
        int x = p.GetProperty("x").GetInt32();
        int y = p.GetProperty("y").GetInt32();
        int w = p.GetProperty("w").GetInt32();
        int h = p.GetProperty("h").GetInt32();
        int dur = p.TryGetProperty("duration_ms", out var d) ? d.GetInt32() : 3000;
        return HighlightOverlay.Highlight(x, y, w, h, dur);
    }

    static object FromPoint(JsonElement p)
    {
        using var automation = new UIA3Automation();
        int x = p.GetProperty("x").GetInt32();
        int y = p.GetProperty("y").GetInt32();
        var elem = automation.FromPoint(new Point(x, y));
        if (elem == null) return new { found = false, error = "no element" };
        return new { found = true, properties = InspectElement(elem) };
    }

    static object InspectFull(JsonElement p)
    {
        using var automation = new UIA3Automation();
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { found = false, error = "no window" };
        var name = GetStr(p, "name");
        var aid = GetStr(p, "automation_id");
        AutomationElement? elem = FindInScope(automation, window, name, aid, p);
        if (elem == null) return new { found = false, error = "not found" };
        return new { found = true, properties = InspectElement(elem) };
    }

    static object InvokeCmd(JsonElement p)
    {
        using var automation = new UIA3Automation();
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { success = false, error = "no window" };
        var name = GetStr(p, "name");
        var aid = GetStr(p, "automation_id");
        var elem = FindInScope(automation, window, name, aid, p);
        if (elem == null) return new { success = false, error = "not found" };
        return ActivateElement(elem);
    }

    /// <summary>Invoke for buttons; SelectionItem for NavView ListItems (UWP).</summary>
    static object ActivateElement(AutomationElement elem)
    {
        if (elem.Patterns.Invoke.IsSupported)
        {
            elem.Patterns.Invoke.Pattern.Invoke();
            return new { success = true, method = "InvokePattern" };
        }
        if (elem.Patterns.SelectionItem.IsSupported)
        {
            elem.Patterns.SelectionItem.Pattern.Select();
            return new { success = true, method = "SelectionItemPattern" };
        }
        if (elem.Patterns.Toggle.IsSupported)
        {
            elem.Patterns.Toggle.Pattern.Toggle();
            return new { success = true, method = "TogglePattern" };
        }
        if (elem.Patterns.ExpandCollapse.IsSupported)
        {
            elem.Patterns.ExpandCollapse.Pattern.Expand();
            return new { success = true, method = "ExpandCollapse.Expand" };
        }
        return new { success = false, error = "No Invoke, SelectionItem, Toggle nor ExpandCollapse supported" };
    }

    static object ExpandCollapseCmd(JsonElement p)
    {
        using var automation = new UIA3Automation();
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { success = false, error = "no window" };
        var name = GetStr(p, "name");
        var aid = GetStr(p, "automation_id");
        var elem = FindInScope(automation, window, name, aid, p);
        if (elem == null) return new { success = false, error = "not found" };
        if (!elem.Patterns.ExpandCollapse.IsSupported)
            return new { success = false, error = "ExpandCollapse not supported" };
        var action = GetStr(p, "action");
        var pattern = elem.Patterns.ExpandCollapse.Pattern;
        if (action.Equals("collapse", StringComparison.OrdinalIgnoreCase))
        {
            pattern.Collapse();
            return new { success = true, method = "ExpandCollapse.Collapse" };
        }
        pattern.Expand();
        return new { success = true, method = "ExpandCollapse.Expand" };
    }

    static bool RectsIntersect(System.Drawing.Rectangle a, System.Drawing.Rectangle b)
    {
        return a.IntersectsWith(b);
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
            if (er.Width <= 0 && er.Height <= 0) return false;
            return RectsIntersect(wr, er);
        }
        catch { return false; }
    }

    static IEnumerable<AutomationElement> DesktopElementsInScope(
        UIA3Automation automation,
        AutomationElement window,
        JsonElement p)
    {
        var desktop = automation.GetDesktop();
        foreach (var e in desktop.FindAllDescendants())
        {
            if (ElementInScope(e, window, p))
                yield return e;
        }
    }

    static AutomationElement? FindInScope(
        UIA3Automation automation,
        AutomationElement window,
        string name,
        string aid,
        JsonElement p)
    {
        AutomationElement? elem = null;
        if (!string.IsNullOrEmpty(aid))
            elem = window.FindFirstDescendant(cf => cf.ByAutomationId(aid));
        if (elem == null && !string.IsNullOrEmpty(name))
            elem = window.FindFirstDescendant(cf => cf.ByName(name));
        if (elem != null) return elem;

        foreach (var e in DesktopElementsInScope(automation, window, p))
        {
            string eAid = "";
            try { eAid = e.AutomationId ?? ""; } catch { }
            if (!string.IsNullOrEmpty(aid) && eAid == aid)
                return e;
            if (!string.IsNullOrEmpty(name) && (e.Name ?? "").Contains(name, StringComparison.OrdinalIgnoreCase))
                return e;
        }
        return null;
    }

    static void SupplementDesktopInScope(
        UIA3Automation automation,
        AutomationElement window,
        JsonElement p,
        int maxDepth,
        bool visibleOnly,
        string roleFilter,
        List<Dictionary<string, object?>> outList)
    {
        var seen = new HashSet<string>();
        foreach (var existing in outList)
        {
            var key = $"{existing.GetValueOrDefault("automation_id")}|{existing.GetValueOrDefault("x")}|{existing.GetValueOrDefault("y")}";
            seen.Add(key);
        }
        try
        {
            foreach (var e in DesktopElementsInScope(automation, window, p))
            {
                if (outList.Count >= 500) break;
                Dictionary<string, object?> info;
                try { info = InspectElement(e); }
                catch { continue; }
                var key = $"{info.GetValueOrDefault("automation_id")}|{info.GetValueOrDefault("x")}|{info.GetValueOrDefault("y")}";
                if (seen.Contains(key)) continue;
                if (visibleOnly && (info["is_offscreen"] as bool? ?? false)) continue;
                var role = info["role"]?.ToString() ?? "";
                if (!string.IsNullOrEmpty(roleFilter) &&
                    !role.Contains(roleFilter, StringComparison.OrdinalIgnoreCase))
                    continue;
                var aid = info["automation_id"]?.ToString() ?? "";
                var ename = info["name"]?.ToString() ?? "";
                if (string.IsNullOrEmpty(aid) && string.IsNullOrEmpty(ename) && role == "Pane")
                    continue;
                outList.Add(info);
                seen.Add(key);
            }
        }
        catch { /* optional */ }
    }

    static object WalkTree(JsonElement p)
    {
        using var automation = new UIA3Automation();
        var window = ResolveWindow(automation, GetStr(p, "window_title"), p);
        if (window == null) return new { elements = Array.Empty<object>() };
        int maxDepth = p.TryGetProperty("max_depth", out var dp) ? dp.GetInt32() : 5;
        bool visibleOnly = p.TryGetProperty("visible_only", out var vp) && vp.GetBoolean();
        string roleFilter = GetStr(p, "role");

        var elements = new List<Dictionary<string, object?>>();
        CollectDescendants(window, maxDepth, visibleOnly, roleFilter, elements);
        SupplementDesktopInScope(automation, window, p, maxDepth, visibleOnly, roleFilter, elements);

        return new { elements, count = elements.Count };
    }

    static void CollectDescendants(
        AutomationElement root,
        int maxDepth,
        bool visibleOnly,
        string roleFilter,
        List<Dictionary<string, object?>> outList)
    {
        try
        {
            foreach (var e in root.FindAllDescendants())
            {
                if (outList.Count >= 500) break;
                TryAddElement(e, 0, maxDepth, visibleOnly, roleFilter, outList);
            }
        }
        catch
        {
            WalkElement(root, 0, maxDepth, visibleOnly, roleFilter, outList);
        }
    }

    static void TryAddElement(
        AutomationElement e,
        int depth,
        int maxDepth,
        bool visibleOnly,
        string roleFilter,
        List<Dictionary<string, object?>> outList)
    {
        if (depth > maxDepth || outList.Count >= 500) return;
        Dictionary<string, object?> info;
        try { info = InspectElement(e); }
        catch { return; }

        if (visibleOnly && (info["is_offscreen"] as bool? ?? false)) return;
        var role = info["role"]?.ToString() ?? "";
        if (!string.IsNullOrEmpty(roleFilter) &&
            !role.Contains(roleFilter, StringComparison.OrdinalIgnoreCase))
            return;
        var aid = info["automation_id"]?.ToString() ?? "";
        var ename = info["name"]?.ToString() ?? "";
        if (string.IsNullOrEmpty(aid) && string.IsNullOrEmpty(ename) && role == "Pane")
            return;
        outList.Add(info);
    }

    static void WalkElement(
        AutomationElement e,
        int depth,
        int maxDepth,
        bool visibleOnly,
        string roleFilter,
        List<Dictionary<string, object?>> outList)
    {
        if (depth > maxDepth || outList.Count >= 500) return;
        Dictionary<string, object?>? info = null;
        try
        {
            info = InspectElement(e);
        }
        catch
        {
            if (depth >= maxDepth) return;
            goto walk_children;
        }

        if (visibleOnly && e.IsOffscreen) { /* skip self but may walk children */ }
        else
        {
            var role = info["role"]?.ToString() ?? "";
            if (string.IsNullOrEmpty(roleFilter) || role.Contains(roleFilter, StringComparison.OrdinalIgnoreCase))
            {
                if (!visibleOnly || !(info["is_offscreen"] as bool? ?? false))
                    if (!string.IsNullOrEmpty(info["name"]?.ToString()) || role != "Pane")
                        outList.Add(info);
            }
        }
        if (depth >= maxDepth) return;

        walk_children:
        try
        {
            foreach (var child in e.FindAllChildren())
                WalkElement(child, depth + 1, maxDepth, visibleOnly, roleFilter, outList);
        }
        catch { /* skip broken subtree */ }
    }

    static Dictionary<string, object?> InspectElement(AutomationElement e)
    {
        var r = e.BoundingRectangle;
        var patterns = new Dictionary<string, object?>();
        try
        {
            if (e.Patterns.Invoke.IsSupported) patterns["Invoke"] = new { supported = true };
            if (e.Patterns.SelectionItem.IsSupported)
            {
                try
                {
                    var sel = e.Patterns.SelectionItem.Pattern;
                    patterns["SelectionItem"] = new
                    {
                        supported = true,
                        is_selected = sel.IsSelected,
                    };
                }
                catch { patterns["SelectionItem"] = new { supported = true }; }
            }
            if (e.Patterns.Value.IsSupported)
            {
                try { patterns["Value"] = new { supported = true, value = e.Patterns.Value.Pattern.Value.Value }; }
                catch { patterns["Value"] = new { supported = true }; }
            }
            if (e.Patterns.Toggle.IsSupported)
            {
                try { patterns["Toggle"] = new { supported = true, state = e.Patterns.Toggle.Pattern.ToggleState.ToString() }; }
                catch { patterns["Toggle"] = new { supported = true }; }
            }
            if (e.Patterns.ExpandCollapse.IsSupported)
            {
                try { patterns["ExpandCollapse"] = new { supported = true, state = e.Patterns.ExpandCollapse.Pattern.ExpandCollapseState.ToString() }; }
                catch { patterns["ExpandCollapse"] = new { supported = true }; }
            }
            if (e.Patterns.LegacyIAccessible.IsSupported) patterns["LegacyIAccessible"] = new { supported = true };
        }
        catch { /* patterns optional */ }

        string automationId = "";
        try { automationId = e.AutomationId ?? ""; } catch { automationId = ""; }

        long hwnd = 0;
        try { hwnd = (long)e.Properties.NativeWindowHandle.ValueOrDefault; } catch { }

        return new Dictionary<string, object?>
        {
            ["name"] = SafeString(() => e.Name ?? ""),
            ["role"] = SafeString(() => e.ControlType.ToString()),
            ["localized_control_type"] = SafeString(() => e.Properties.LocalizedControlType.ValueOrDefault ?? ""),
            ["x"] = (int)r.X,
            ["y"] = (int)r.Y,
            ["width"] = (int)r.Width,
            ["height"] = (int)r.Height,
            ["automation_id"] = automationId,
            ["class_name"] = SafeString(() => e.ClassName ?? ""),
            ["framework_id"] = SafeString(() => e.Properties.FrameworkId.ValueOrDefault ?? ""),
            ["process_id"] = SafeInt(() => e.Properties.ProcessId.ValueOrDefault),
            ["native_window_handle"] = hwnd,
            ["access_key"] = SafeString(() => e.Properties.AccessKey.ValueOrDefault ?? ""),
            ["accelerator_key"] = SafeString(() => e.Properties.AcceleratorKey.ValueOrDefault ?? ""),
            ["help_text"] = SafeString(() => e.Properties.HelpText.ValueOrDefault ?? ""),
            ["item_status"] = SafeString(() => e.Properties.ItemStatus.ValueOrDefault ?? ""),
            ["item_type"] = SafeString(() => e.Properties.ItemType.ValueOrDefault ?? ""),
            ["aria_role"] = SafeString(() => e.Properties.AriaRole.ValueOrDefault ?? ""),
            ["aria_properties"] = SafeString(() => e.Properties.AriaProperties.ValueOrDefault ?? ""),
            ["is_enabled"] = SafeBool(() => e.IsEnabled),
            ["is_offscreen"] = SafeBool(() => e.IsOffscreen),
            ["has_keyboard_focus"] = SafeBool(() => e.Properties.HasKeyboardFocus.ValueOrDefault),
            ["is_keyboard_focusable"] = SafeBool(() => e.Properties.IsKeyboardFocusable.ValueOrDefault),
            ["is_password"] = SafeBool(() => e.Properties.IsPassword.ValueOrDefault),
            ["is_content_element"] = SafeBool(() => e.Properties.IsContentElement.ValueOrDefault),
            ["is_control_element"] = SafeBool(() => e.Properties.IsControlElement.ValueOrDefault),
            ["patterns"] = patterns,
        };
    }

    static string SafeString(Func<string> getter)
    {
        try { return getter(); }
        catch { return ""; }
    }

    static int SafeInt(Func<int> getter)
    {
        try { return getter(); }
        catch { return 0; }
    }

    static bool SafeBool(Func<bool> getter)
    {
        try { return getter(); }
        catch { return false; }
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
            if (fg != null)
            {
                var w = fg.AsWindow();
                if (w != null) return w;
                return fg;
            }
            return desktop.FindFirstDescendant(cf => cf.ByControlType(ControlType.Window));
        }

        var titleLower = title.ToLowerInvariant();
        AutomationElement? best = null;
        var bestScore = int.MinValue;
        foreach (var window in desktop.FindAllDescendants(cf => cf.ByControlType(ControlType.Window)))
        {
            var name = window.Name ?? "";
            if (!name.Contains(title, StringComparison.OrdinalIgnoreCase))
                continue;
            var r = window.BoundingRectangle;
            var score = 0;
            if (name.Equals(title, StringComparison.OrdinalIgnoreCase)) score += 10000;
            if (r.X > -1000 && r.Y > -1000) score += 500;
            score += (int)(r.Width * r.Height) / 1000;
            var cls = (window.ClassName ?? "").ToLowerInvariant();
            if (titleLower is "calculadora" or "calculator")
            {
                // Title chrome (HistoryButton, TogglePaneButton) lives on ApplicationFrameHost,
                // not CoreWindow — prefer frame host for find/invoke scope.
                if (cls.Contains("applicationframe")) score += 12000;
                else if (cls.Contains("corewindow")) score += 8000;
            }
            else if (cls.Contains("applicationframe")) score += 100;
            if (score > bestScore)
            {
                bestScore = score;
                best = window;
            }
        }
        return best;
    }

    static string GetStr(JsonElement p, string key) =>
        p.TryGetProperty(key, out var v) ? v.GetString() ?? "" : "";
}

class Request
{
    public string Command { get; set; } = "";
    public JsonElement Params { get; set; }
}
