-- Classic Forever: panel para los bots de mazmorra (.dungeonbots del servidor Classic Forever).
-- Estetica del launcher: cuero, bordes dorados (#E8C46A), logo. Las ordenes van por el chat como comandos del servidor:
--   .dungeonbots <mazmorra> [tank|healer|dps]      llenar el grupo
--   .dungeonbots start|stop|wait|follow|pull|rest  ordenes (servidor con !dbot_orders_off_1601 apagado)
--   .dungeonbots attack|pulltarget|skip|back    tu objetivo, saltar paso, volver a la entrada
--   .dungeonbots watch on                        estado en vivo: lineas "[CFB]..." por mensaje de sistema (se ocultan del chat)
--   .dungeonbots status | dismiss
local ADDON, ns = ...
local L = setmetatable({}, { __index = function(_, k) return ns.L[k] end })

local GOLD = { 0.91, 0.77, 0.42 }
local MEDIA = "Interface\\AddOns\\" .. ADDON .. "\\Media\\"
local ORDER_KEYS = { start = "Start", stop = "Stop", follow = "Follow", wait = "Wait", pull = "Pull", rest = "Rest",
                     attack = "Attack", pulltarget = "PullTarget", skip = "Skip", back = "Back" }
local STATE_ORDERS = { start = "auto", stop = "stop", follow = "follow", wait = "wait", back = "auto" }
local ORDER_STATE_TEXT = { auto = "OrdAuto", stop = "OrdStop", wait = "OrdWait", follow = "OrdFollow" }
local STATE_BUTTON = { auto = "start", stop = "stop", wait = "wait", follow = "follow" }

local defaults = {
    alpha = 1.0, scale = 1.0, autoShow = true, minimap = true, locked = false, minimapAngle = 200,
    dungeon = "auto", role = "auto", lang = "auto",
}

local db
local lastOrder          -- orden de estado (auto/stop/wait/follow): la del servidor si llega el estado en vivo
local pendingUntil = 0
local live               -- ultimo estado en vivo: { on, order, step, steps, done, combat, key, focus, bots = {...} }
local watchSent = false

-- ------------------------------------------------------------------------------------------------ utilidades
local function Print(msg)
    DEFAULT_CHAT_FRAME:AddMessage("|cffE8C46A[Classic Forever]|r " .. msg)
end

local function CurrentDungeon()
    local instanceID = select(8, GetInstanceInfo())
    for _, d in ipairs(ns.Dungeons) do
        if d.map == instanceID then return d end
    end
end

local function FindDungeon(key)
    for _, d in ipairs(ns.Dungeons) do
        if d.key == key then return d end
    end
end

local function SelectedDungeon()
    if db.dungeon == "auto" then return CurrentDungeon() end
    return FindDungeon(db.dungeon)
end

local function Send(args)
    pendingUntil = GetTime() + 3
    SendChatMessage(".dungeonbots " .. args, "SAY")
end

-- estado en vivo: se pide una vez por conexion (el servidor lo manda hasta que desconectas)
local function WatchOn()
    if not watchSent then
        watchSent = true
        Send("watch on")
    end
end

local function IsLeaderOrSolo()
    return not IsInGroup() or UnitIsGroupLeader("player")
end

-- ------------------------------------------------------------------------------------------------ ventana
local F = CreateFrame("Frame", "CFBotsFrame", UIParent, BackdropTemplateMixin and "BackdropTemplate" or nil)
F:SetSize(300, 648)
F:SetPoint("CENTER")
F:SetFrameStrata("MEDIUM")
F:SetClampedToScreen(true)
F:Hide()
F:SetBackdrop({
    edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", edgeSize = 16,
    insets = { left = 4, right = 4, top = 4, bottom = 4 },
})
F:SetBackdropBorderColor(GOLD[1], GOLD[2], GOLD[3], 1)
tinsert(UISpecialFrames, "CFBotsFrame")   -- Escape la cierra

local bg = F:CreateTexture(nil, "BACKGROUND")
bg:SetPoint("TOPLEFT", 4, -4)
bg:SetPoint("BOTTOMRIGHT", -4, 4)
bg:SetTexture(MEDIA .. "leather")
local shade = F:CreateTexture(nil, "BACKGROUND", nil, 1)
shade:SetAllPoints(bg)
shade:SetColorTexture(0, 0, 0, 0.25)

local footerBg = F:CreateTexture(nil, "BORDER")
footerBg:SetPoint("BOTTOMLEFT", 4, 4)
footerBg:SetPoint("BOTTOMRIGHT", -4, 4)
footerBg:SetHeight(84)
footerBg:SetTexture(MEDIA .. "marble")

local function Line(parent, y)
    local t = parent:CreateTexture(nil, "ARTWORK")
    t:SetColorTexture(GOLD[1], GOLD[2], GOLD[3], 0.45)
    t:SetHeight(1)
    t:SetPoint("TOPLEFT", 14, y)
    t:SetPoint("TOPRIGHT", -14, y)
    return t
end

F:EnableMouse(true)
F:SetMovable(true)
F:RegisterForDrag("LeftButton")
F:SetScript("OnDragStart", function(self) if not db.locked then self:StartMoving() end end)
F:SetScript("OnDragStop", function(self)
    self:StopMovingOrSizing()
    local point, _, rel, x, y = self:GetPoint()
    db.point, db.rel, db.x, db.y = point, rel, x, y
end)

local logo = F:CreateTexture(nil, "OVERLAY")
logo:SetTexture(MEDIA .. "logo")
logo:SetSize(66, 66)
logo:SetPoint("TOPLEFT", -12, 16)

local title = F:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
title:SetPoint("TOPLEFT", 58, -12)
title:SetTextColor(GOLD[1], GOLD[2], GOLD[3])
local subtitle = F:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
subtitle:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -2)

local closeBtn = CreateFrame("Button", nil, F, "UIPanelCloseButton")
closeBtn:SetPoint("TOPRIGHT", 0, 0)

local gear = CreateFrame("Button", nil, F)
gear:SetSize(20, 20)
gear:SetPoint("RIGHT", closeBtn, "LEFT", 0, 0)
gear:SetNormalTexture("Interface\\Icons\\Trade_Engineering")
gear:GetNormalTexture():SetTexCoord(0.08, 0.92, 0.08, 0.92)
gear:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")

local Main = CreateFrame("Frame", nil, F)
Main:SetAllPoints()
local Opts = CreateFrame("Frame", nil, F)
Opts:SetAllPoints()
Opts:Hide()

Line(F, -52)

local function Tip(widget, textKey)
    widget:HookScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(self.tipTitle or "", GOLD[1], GOLD[2], GOLD[3])
        GameTooltip:AddLine(L[textKey], 1, 1, 1, true)
        GameTooltip:Show()
    end)
    widget:HookScript("OnLeave", function() GameTooltip:Hide() end)
end

local function Header(parent, y)
    local fs = parent:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    fs:SetPoint("TOPLEFT", 18, y)
    fs:SetTextColor(GOLD[1], GOLD[2], GOLD[3])
    return fs
end

local function Button(parent, w, h)
    local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    b:SetSize(w, h)
    return b
end

-- ------------------------------------------------------------------------------------------------ mazmorra y rol
local hDungeon = Header(Main, -62)

local dungeonLabel = Main:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
dungeonLabel:SetPoint("TOPLEFT", 20, -86)
local dungeonDD = CreateFrame("Frame", "CFBotsDungeonDropDown", Main, "UIDropDownMenuTemplate")
dungeonDD:SetPoint("TOPLEFT", 80, -78)
UIDropDownMenu_SetWidth(dungeonDD, 170)

local roleLabel = Main:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
roleLabel:SetPoint("TOPLEFT", 20, -118)
local roleDD = CreateFrame("Frame", "CFBotsRoleDropDown", Main, "UIDropDownMenuTemplate")
roleDD:SetPoint("TOPLEFT", 80, -110)
UIDropDownMenu_SetWidth(roleDD, 170)

local levelsText = Main:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
levelsText:SetPoint("TOPLEFT", 100, -140)

local fillBtn = Button(Main, 250, 28)
fillBtn:SetPoint("TOP", 0, -158)
Tip(fillBtn, "TipFill")

local function DungeonText()
    if db.dungeon == "auto" then
        local d = CurrentDungeon()
        return d and L.AutoDetected:format(ns.DungeonName(d)) or L.AutoNone
    end
    local d = FindDungeon(db.dungeon)
    return d and ns.DungeonName(d) or db.dungeon
end

local function RoleText()
    if db.role == "tank" then return L.Tank elseif db.role == "healer" then return L.Healer elseif db.role == "dps" then return L.Dps end
    return L.RoleAuto
end

local Refresh   -- se define abajo

-- El cliente llama a estas funciones ya en UIDropDownMenu_Initialize: se registran en ADDON_LOADED (con db cargado)
local function InitDungeonMenu(self, level)
    if not db then return end
    local info = UIDropDownMenu_CreateInfo()
    info.text, info.value, info.checked = L.AutoDetected:format(CurrentDungeon() and ns.DungeonName(CurrentDungeon()) or "—"), "auto", db.dungeon == "auto"
    info.func = function() db.dungeon = "auto"; Refresh() end
    UIDropDownMenu_AddButton(info, level)
    for _, d in ipairs(ns.Dungeons) do
        info = UIDropDownMenu_CreateInfo()
        info.text = ns.DungeonName(d) .. "  |cff9C9076" .. d.min .. "-" .. d.max .. "|r"
        info.value, info.checked = d.key, db.dungeon == d.key
        info.func = function() db.dungeon = d.key; Refresh() end
        UIDropDownMenu_AddButton(info, level)
    end
end

local function InitRoleMenu(self, level)
    if not db then return end
    for _, r in ipairs({ { "auto", "RoleAuto" }, { "tank", "Tank" }, { "healer", "Healer" }, { "dps", "Dps" } }) do
        local info = UIDropDownMenu_CreateInfo()
        info.text, info.value, info.checked = L[r[2]], r[1], db.role == r[1]
        info.func = function() db.role = r[1]; Refresh() end
        UIDropDownMenu_AddButton(info, level)
    end
end

local function FillGroup(key, role)
    local d = key and FindDungeon(key) or SelectedDungeon()
    local k = d and d.key or key
    if not k then
        Print(L.NoDungeon)
        return
    end
    role = role or (db.role ~= "auto" and db.role) or nil
    Send(k .. (role and (" " .. role) or ""))
end
fillBtn:SetScript("OnClick", function() FillGroup(); WatchOn() end)

-- ------------------------------------------------------------------------------------------------ ordenes
Line(Main, -196)
local hOrders = Header(Main, -206)

local orderButtons = {}
local function Order(key)
    if not IsLeaderOrSolo() then
        Print(L.NotInGroupLead)
        return
    end
    if STATE_ORDERS[key] then lastOrder = STATE_ORDERS[key] end
    Send(key)
    WatchOn()
    Refresh()
end

local layout = { { "start", "stop" }, { "follow", "wait" }, { "pull", "rest" }, { "attack", "pulltarget" }, { "skip", "back" } }
for row, pair in ipairs(layout) do
    for col, key in ipairs(pair) do
        local b = Button(Main, 128, 26)
        b:SetPoint("TOPLEFT", col == 1 and 18 or 154, -226 - (row - 1) * 30)
        b:SetScript("OnClick", function() Order(key) end)
        Tip(b, "Tip" .. ORDER_KEYS[key])
        orderButtons[key] = b
    end
end

local marksText = Main:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
marksText:SetPoint("TOPLEFT", 18, -380)
marksText:SetPoint("TOPRIGHT", -18, -380)
marksText:SetJustifyH("LEFT")
local function Icon(n) return "|TInterface\\TargetingFrame\\UI-RaidTargetingIcon_" .. n .. ":13|t" end

-- ------------------------------------------------------------------------------------------------ grupo en vivo
Line(Main, -408)
local hGroup = Header(Main, -418)
local summary = Main:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
summary:SetPoint("TOPLEFT", 18, -438)
summary:SetPoint("TOPRIGHT", -18, -438)
summary:SetJustifyH("LEFT")

local ROLE_TEXT = { T = "|cff6FA8DCT|r", H = "|cff5CD67AH|r", D = "|cffE05A4ED|r" }
local rows = {}
for i = 1, 4 do
    local r = CreateFrame("Frame", nil, Main)
    r:SetSize(264, 24)
    r:SetPoint("TOPLEFT", 18, -456 - (i - 1) * 26)
    r.role = r:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    r.role:SetPoint("LEFT", 0, 0)
    r.name = r:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    r.name:SetPoint("LEFT", 14, 0)
    r.name:SetWidth(96)
    r.name:SetJustifyH("LEFT")
    local function Bar(h, y, cr, cg, cb)
        local b = CreateFrame("StatusBar", nil, r)
        b:SetSize(150, h)
        b:SetPoint("TOPRIGHT", 0, y)
        b:SetStatusBarTexture("Interface\\TargetingFrame\\UI-StatusBar")
        b:SetStatusBarColor(cr, cg, cb)
        b:SetMinMaxValues(0, 100)
        local back = b:CreateTexture(nil, "BACKGROUND")
        back:SetAllPoints()
        back:SetColorTexture(0, 0, 0, 0.55)
        return b
    end
    r.hp = Bar(12, -2, 0.36, 0.84, 0.48)
    r.mana = Bar(6, -15, 0.27, 0.51, 0.95)
    r.hpText = r.hp:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    r.hpText:SetPoint("CENTER", 0, 0)
    r.hpText:SetFont(r.hpText:GetFont(), 9, "OUTLINE")
    r:Hide()
    rows[i] = r
end

local function ClassColor(classID)
    local _, file = GetClassInfo and GetClassInfo(classID)
    local c = file and RAID_CLASS_COLORS and RAID_CLASS_COLORS[file]
    return c and c.r or 1, c and c.g or 1, c and c.b or 1
end

local function RenderLive()
    if not live then
        summary:SetText(watchSent and L.WaitingData or L.NoBots)
        for _, r in ipairs(rows) do r:Hide() end
        return
    end
    if not live.on then
        summary:SetText(L.NoBots)
        for _, r in ipairs(rows) do r:Hide() end
        return
    end
    local parts = { live.done and L.RouteDone or L.StepOf:format(live.step, live.steps),
                    "|cffE8C46A" .. L[ORDER_STATE_TEXT[live.order] or "OrdAuto"] .. "|r" }
    if live.combat then parts[#parts + 1] = "|cffE05A4E" .. L.InCombat .. "|r" end
    if live.focus ~= "" then parts[#parts + 1] = L.FocusOn:format(live.focus) end
    summary:SetText(table.concat(parts, "  ·  "))
    for i, r in ipairs(rows) do
        local b = live.bots[i]
        if b then
            r.role:SetText(ROLE_TEXT[b.role] or b.role)
            local cr, cg, cb = ClassColor(b.class)
            if not b.alive then cr, cg, cb = 0.5, 0.5, 0.5 end
            r.name:SetText(b.name)
            r.name:SetTextColor(cr, cg, cb)
            r.hp:SetValue(b.alive and b.hp or 0)
            r.hpText:SetText(not b.alive and L.Dead or (b.resting and L.Resting) or (b.hp .. "%"))
            r.mana:SetShown(b.mana >= 0)
            r.mana:SetValue(math.max(b.mana, 0))
            r:Show()
        else
            r:Hide()
        end
    end
end

-- "[CFB]1|orden|paso|pasos|terminada|combate|preset|objetivo;bot,rol,clase,vida,mana,vivo,descansando;..." o "[CFB]0"
local function ParseLive(msg)
    local body = msg:sub(6)
    if body == "0" then live = { on = false }; lastOrder = nil; return true end
    if body:sub(1, 2) ~= "1|" then return false end
    local head, rest = body:match("^([^;]*)(.*)$")
    local f = { strsplit("|", head) }
    live = { on = true, order = f[2], step = tonumber(f[3]) or 0, steps = tonumber(f[4]) or 0, done = f[5] == "1",
             combat = f[6] == "1", key = f[7], focus = f[8] or "", bots = {} }
    for chunk in rest:gmatch(";([^;]+)") do
        local name, role, class, hp, mana, alive, resting = strsplit(",", chunk)
        live.bots[#live.bots + 1] = { name = name, role = role, class = tonumber(class), hp = tonumber(hp) or 0,
            mana = tonumber(mana) or -1, alive = alive == "1", resting = resting == "1" }
    end
    lastOrder = live.order
    return true
end

-- ------------------------------------------------------------------------------------------------ pie: respuesta del servidor, estado, despedir
local reply = Main:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
reply:SetPoint("BOTTOMLEFT", 16, 50)
reply:SetPoint("BOTTOMRIGHT", -16, 50)
reply:SetJustifyH("LEFT")
reply:SetHeight(28)
reply:SetWordWrap(true)
reply:SetTextColor(0.84, 0.80, 0.71)

local statusBtn = Button(Main, 128, 24)
statusBtn:SetPoint("BOTTOMLEFT", 18, 16)
statusBtn:SetScript("OnClick", function() Send("status"); WatchOn() end)
Tip(statusBtn, "TipStatus")

local dismissBtn = Button(Main, 128, 24)
dismissBtn:SetPoint("BOTTOMRIGHT", -18, 16)
dismissBtn:SetScript("OnClick", function() StaticPopup_Show("CFBOTS_DISMISS") end)
Tip(dismissBtn, "TipDismiss")

StaticPopupDialogs["CFBOTS_DISMISS"] = {
    text = "", button1 = ACCEPT, button2 = CANCEL,
    OnShow = function(self) self.text:SetText(L.WarningDismiss) end,
    OnAccept = function() lastOrder = nil; Send("dismiss"); WatchOn(); Refresh() end,
    timeout = 0, whileDead = true, hideOnEscape = true, preferredIndex = 3,
}

-- ------------------------------------------------------------------------------------------------ ajustes
local hOpts = Header(Opts, -62)

local function Slider(name, y, min, max, step, get, set)
    local s = CreateFrame("Slider", name, Opts, "OptionsSliderTemplate")
    s:SetPoint("TOP", 0, y)
    s:SetWidth(220)
    s:SetMinMaxValues(min, max)
    s:SetValueStep(step)
    s:SetObeyStepOnDrag(true)
    _G[name .. "Low"]:SetText(math.floor(min * 100) .. "%")
    _G[name .. "High"]:SetText(math.floor(max * 100) .. "%")
    s:SetScript("OnValueChanged", function(_, v) set(v) end)
    s.Refresh = function() s:SetValue(get()) end
    return s
end

local alpha = Slider("CFBotsAlphaSlider", -100, 0.3, 1.0, 0.05, function() return db.alpha end,
    function(v) db.alpha = v; F:SetAlpha(v) end)
local scale = Slider("CFBotsScaleSlider", -150, 0.7, 1.3, 0.05, function() return db.scale end,
    function(v) db.scale = v; F:SetScale(v) end)

local function Check(y, key, onChange)
    local c = CreateFrame("CheckButton", nil, Opts, "UICheckButtonTemplate")
    c:SetPoint("TOPLEFT", 22, y)
    c:SetSize(26, 26)
    c.label = c:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    c.label:SetPoint("LEFT", c, "RIGHT", 2, 0)
    c:SetScript("OnClick", function(self) db[key] = self:GetChecked() and true or false; if onChange then onChange() end end)
    c.Refresh = function() c:SetChecked(db[key]) end
    return c
end

local UpdateMinimap   -- abajo
local cAuto = Check(-186, "autoShow")
local cMinimap = Check(-214, "minimap", function() UpdateMinimap() end)
local cLock = Check(-242, "locked")

local langES = Button(Opts, 60, 22)
langES:SetPoint("TOPLEFT", 26, -282)
langES:SetText("ES")
local langEN = Button(Opts, 60, 22)
langEN:SetPoint("LEFT", langES, "RIGHT", 6, 0)
langEN:SetText("EN")
local langAuto = Button(Opts, 60, 22)
langAuto:SetPoint("LEFT", langEN, "RIGHT", 6, 0)
langAuto:SetText("Auto")
local function SetLang(code) db.lang = code; ns.SetLanguage(code); Refresh() end
langES:SetScript("OnClick", function() SetLang("es") end)
langEN:SetScript("OnClick", function() SetLang("en") end)
langAuto:SetScript("OnClick", function() SetLang("auto") end)

local backBtn = Button(Opts, 120, 24)
backBtn:SetPoint("BOTTOM", 0, 30)
backBtn:SetScript("OnClick", function() Opts:Hide(); Main:Show() end)
gear:SetScript("OnClick", function()
    if Opts:IsShown() then Opts:Hide(); Main:Show() else Main:Hide(); Opts:Show() end
end)

-- ------------------------------------------------------------------------------------------------ boton del minimapa
local mm = CreateFrame("Button", "CFBotsMinimapButton", Minimap)
mm:SetSize(31, 31)
mm:SetFrameStrata("MEDIUM")
mm:SetFrameLevel(8)
mm:RegisterForClicks("LeftButtonUp", "RightButtonUp")
mm:RegisterForDrag("LeftButton")
mm:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
local mmIcon = mm:CreateTexture(nil, "BACKGROUND")
mmIcon:SetTexture(MEDIA .. "minimap")
mmIcon:SetSize(20, 20)
mmIcon:SetPoint("TOPLEFT", 6, -5)
local mmBorder = mm:CreateTexture(nil, "OVERLAY")
mmBorder:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
mmBorder:SetSize(53, 53)
mmBorder:SetPoint("TOPLEFT")

local function PlaceMinimap()
    local a = math.rad(db.minimapAngle or 200)
    mm:ClearAllPoints()
    mm:SetPoint("CENTER", Minimap, "CENTER", math.cos(a) * 80, math.sin(a) * 80)
end

mm:SetScript("OnDragStart", function(self)
    self:SetScript("OnUpdate", function()
        local mx, my = Minimap:GetCenter()
        local cx, cy = GetCursorPosition()
        local s = Minimap:GetEffectiveScale()
        db.minimapAngle = math.deg(math.atan2(cy / s - my, cx / s - mx))
        PlaceMinimap()
    end)
end)
mm:SetScript("OnDragStop", function(self) self:SetScript("OnUpdate", nil) end)
mm:SetScript("OnClick", function(_, button)
    if button == "RightButton" then
        Main:Hide(); Opts:Show(); F:Show()
    else
        F:SetShown(not F:IsShown())
    end
end)
mm:SetScript("OnEnter", function(self)
    GameTooltip:SetOwner(self, "ANCHOR_LEFT")
    GameTooltip:SetText("Classic Forever: " .. L.Subtitle, GOLD[1], GOLD[2], GOLD[3])
    GameTooltip:AddLine("/bots", 1, 1, 1)
    GameTooltip:Show()
end)
mm:SetScript("OnLeave", function() GameTooltip:Hide() end)

UpdateMinimap = function()
    mm:SetShown(db.minimap)
    PlaceMinimap()
end

-- ------------------------------------------------------------------------------------------------ textos (idioma) y estado
Refresh = function()
    if not db then return end
    title:SetText(L.Title)
    subtitle:SetText(L.Subtitle)
    hDungeon:SetText(L.Dungeon)
    dungeonLabel:SetText(L.Dungeon)
    roleLabel:SetText(L.YourRole)
    UIDropDownMenu_SetText(dungeonDD, DungeonText())
    UIDropDownMenu_SetText(roleDD, RoleText())
    local d = SelectedDungeon()
    levelsText:SetText(d and L.Levels:format(d.min, d.max) or "")
    fillBtn:SetText(L.FillGroup)
    fillBtn:SetEnabled(d ~= nil)
    hOrders:SetText(L.Orders)
    for key, b in pairs(orderButtons) do
        b:SetText(L[ORDER_KEYS[key]])
        b.tipTitle = L[ORDER_KEYS[key]]
        if lastOrder and STATE_BUTTON[lastOrder] == key then b:LockHighlight() else b:UnlockHighlight() end
    end
    fillBtn.tipTitle = L.FillGroup
    marksText:SetText((L.Marks:gsub("{skull}", Icon(8)):gsub("{cross}", Icon(7)):gsub("{moon}", Icon(5))))
    hGroup:SetText(L.Group)
    RenderLive()
    statusBtn:SetText(L.Status); statusBtn.tipTitle = L.Status
    dismissBtn:SetText("|cffE05A4E" .. L.Dismiss .. "|r"); dismissBtn.tipTitle = L.Dismiss
    hOpts:SetText(L.Settings)
    _G.CFBotsAlphaSliderText:SetText(L.Opacity)
    _G.CFBotsScaleSliderText:SetText(L.Scale)
    cAuto.label:SetText(L.AutoShow)
    cMinimap.label:SetText(L.ShowMinimap)
    cLock.label:SetText(L.LockFrame)
    backBtn:SetText(L.BackBtn)
    gear.tipTitle = L.Settings
    alpha.Refresh(); scale.Refresh(); cAuto.Refresh(); cMinimap.Refresh(); cLock.Refresh()
    BINDING_HEADER_CFBOTS = "Classic Forever: " .. L.Subtitle
    BINDING_NAME_CFBOTS_TOGGLE = L.Subtitle
    for key, name in pairs(ORDER_KEYS) do _G["BINDING_NAME_CFBOTS_" .. key:upper()] = L[name] end
end

F:SetScript("OnShow", Refresh)

-- ------------------------------------------------------------------------------------------------ eventos
local ev = CreateFrame("Frame")
ev:RegisterEvent("ADDON_LOADED")
ev:RegisterEvent("PLAYER_ENTERING_WORLD")
ev:RegisterEvent("ZONE_CHANGED_NEW_AREA")
ev:RegisterEvent("CHAT_MSG_SYSTEM")
ev:SetScript("OnEvent", function(_, event, arg1)
    if event == "ADDON_LOADED" and arg1 == ADDON then
        CFBotsConfig = type(CFBotsConfig) == "table" and CFBotsConfig or {}
        db = CFBotsConfig
        for k, v in pairs(defaults) do if db[k] == nil then db[k] = v end end
        ns.SetLanguage(db.lang)
        if db.point then F:ClearAllPoints(); F:SetPoint(db.point, UIParent, db.rel, db.x, db.y) end
        F:SetAlpha(db.alpha)
        F:SetScale(db.scale)
        UIDropDownMenu_Initialize(dungeonDD, InitDungeonMenu)
        UIDropDownMenu_Initialize(roleDD, InitRoleMenu)
        UpdateMinimap()
        Refresh()
    elseif event == "PLAYER_ENTERING_WORLD" or event == "ZONE_CHANGED_NEW_AREA" then
        if not db then return end
        if event == "PLAYER_ENTERING_WORLD" then watchSent = false end   -- tras un reinicio del servidor hay que volver a pedirlo
        if CurrentDungeon() then
            WatchOn()   -- dentro de una instancia /say no necesita un clic
            if db.autoShow and not F:IsShown() then F:Show() end
        end
        Refresh()
    elseif event == "CHAT_MSG_SYSTEM" and arg1 and arg1:find("^%[CFB%]") then
        if ParseLive(arg1) then RenderLive() end
    elseif event == "CHAT_MSG_SYSTEM" then
        -- respuesta del servidor a lo que acabamos de mandar (las ordenes empiezan por "Bots:")
        if GetTime() < pendingUntil or (arg1 and arg1:find("^Bots:")) then
            reply:SetText(arg1)
            pendingUntil = 0
        end
    end
end)

-- las lineas de estado en vivo no se ven en el chat
ChatFrame_AddMessageEventFilter("CHAT_MSG_SYSTEM", function(_, _, msg)
    return msg and msg:find("^%[CFB%]") ~= nil
end)

-- ------------------------------------------------------------------------------------------------ atajos y /bots
function CFBots_Toggle() F:SetShown(not F:IsShown()) end
function CFBots_Order(key) Order(key) end

SLASH_CFBOTS1 = "/bots"
SLASH_CFBOTS2 = "/cfbots"
SlashCmdList["CFBOTS"] = function(msg)
    local cmd, a, b = strsplit(" ", strtrim(msg or ""):lower())
    if cmd == "" then
        CFBots_Toggle()
    elseif ORDER_KEYS[cmd] then
        Order(cmd)
    elseif cmd == "fill" then
        if a and not FindDungeon(a) and (a == "tank" or a == "healer" or a == "dps") then a, b = nil, a end
        FillGroup(a, b)
    elseif cmd == "status" then
        Send("status")
    elseif cmd == "dismiss" then
        StaticPopup_Show("CFBOTS_DISMISS")
    elseif cmd == "lang" then
        db.lang = a or "auto"; ns.SetLanguage(db.lang); Refresh()
    else
        for line in L.Help:gmatch("[^\n]+") do Print(line) end
    end
end
