import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
from models.currency import Currency
from models.games import Horse, HorseRace
from config import get_config_value

class HorseRaceCog(commands.Cog):
    """賽馬遊戲指令"""

    def __init__(self, bot):
        self.bot = bot
        self.race_system = HorseRace(bot)
        
        # 從配置中獲取賽馬頻道
        race_channel_id = get_config_value('race_channel')
        if race_channel_id:
            self.race_system.race_channel = bot.get_channel(race_channel_id)
            
        # 啟動賽馬排程
        self.race_schedule.start()
        
    def cog_unload(self):
        """Cog 卸載時停止任務"""
        self.race_schedule.cancel()
        
    @tasks.loop(minutes=60)
    async def race_schedule(self):
        """每一小時舉行一場比賽"""
        if self.race_system.race_channel:
            await self.start_betting_phase()
            
    @race_schedule.before_loop
    async def before_race_schedule(self):
        """等待機器人準備好後再開始任務"""
        await self.bot.wait_until_ready()
        
    async def start_betting_phase(self):
        """開始下注階段"""
        if self.race_system.is_race_active:
            return

        self.race_system.is_race_active = True
        self.race_system.betting_open = True
        self.race_system.bets = {}

        embed = discord.Embed(
            title="🏇 賽馬比賽即將開始！",
            description="距離比賽開始還有5分鐘！\n使用 `/horserace [馬號] [金額]` 來下注",
            color=discord.Color.green()
        )

        # 顯示所有馬匹資訊
        horses_info = ""
        for horse in self.race_system.horses:
            horses_info += f"#{horse.number} {horse.emoji} {horse.name}\n"
        embed.add_field(name="參賽馬匹", value=horses_info)

        await self.race_system.race_channel.send(embed=embed)
        
        # 等待4分鐘後發送提醒
        await asyncio.sleep(240)
        if self.race_system.betting_open:
            await self.race_system.race_channel.send("⚠️ 距離比賽開始還有1分鐘！請盡快下注！")
        
        # 再等待1分鐘後開始比賽
        await asyncio.sleep(60)
        self.race_system.betting_open = False
        await self.start_race()

    async def start_race(self):
        """開始賽馬比賽"""
        embed = discord.Embed(
            title="🏁 賽馬比賽開始！",
            description="比賽開始！讓我們看看誰會是最後的贏家！",
            color=discord.Color.gold()
        )
        race_msg = await self.race_system.race_channel.send(embed=embed)

        # 重置所有馬匹位置
        for horse in self.race_system.horses:
            horse.position = 0
            horse.finished = False
            horse.special_event = None

        finished_horses = []
        race_ongoing = True
        
        while race_ongoing:
            # 更新每匹馬的位置
            race_ongoing = False
            for horse in self.race_system.horses:
                if not horse.finished:
                    race_ongoing = True
                    # 隨機移動1-3格
                    move = random.randint(1, 3)
                    
                    # 10%機率觸發特殊事件
                    if random.random() < 0.1 and not horse.special_event:
                        event = random.choice(self.race_system.special_events)
                        horse.special_event = event
                        if "向前" in event or "提升" in event or "大增" in event:
                            move += random.randint(2, 3)
                        elif "後退" in event or "滑倒" in event or "停下" in event or "繞路" in event:
                            move = -random.randint(1, 2)
                            
                    horse.position = max(0, min(self.race_system.track_length, horse.position + move))
                    
                    # 檢查是否到達終點
                    if horse.position >= self.race_system.track_length and not horse.finished:
                        horse.finished = True
                        finished_horses.append(horse)

            # 更新賽道顯示
            track_display = ""
            for horse in self.race_system.horses:
                # 建立賽道
                track = "." * self.race_system.track_length
                if horse.position < self.race_system.track_length:
                    track = track[:horse.position] + horse.emoji + track[horse.position + 1:]
                else:
                    track = track[:self.race_system.track_length - 1] + horse.emoji
                
                # 添加特殊事件顯示
                event_display = f" 👉 {horse.special_event}" if horse.special_event else ""
                track_display += f"#{horse.number} {track}{event_display}\n"

            embed.description = f"```\n{track_display}\n```"
            await race_msg.edit(embed=embed)
            await asyncio.sleep(1.5)  # 延遲1.5秒更新一次

        # 比賽結束，公布結果
        await self.end_race(finished_horses)

    async def end_race(self, finished_horses):
        """結束比賽並結算獎金"""
        result_embed = discord.Embed(
            title="🏆 賽馬比賽結束！",
            color=discord.Color.gold()
        )

        # 添加比賽結果
        result_text = ""
        for i, horse in enumerate(finished_horses):
            if i == 0:
                result_text += f"🥇 第一名：{horse.emoji} #{horse.number} {horse.name}\n"
            elif i == 1:
                result_text += f"🥈 第二名：{horse.emoji} #{horse.number} {horse.name}\n"
            elif i == 2:
                result_text += f"🥉 第三名：{horse.emoji} #{horse.number} {horse.name}\n"
            else:
                result_text += f"第{i+1}名：{horse.emoji} #{horse.number} {horse.name}\n"

        result_embed.add_field(name="比賽結果", value=result_text, inline=False)

        # 計算和發放獎金
        winning_horse = finished_horses[0]
        total_pool = 0
        winning_pool = 0
        
        for user_id, bets in self.race_system.bets.items():
            for horse_num, amount in bets.items():
                total_pool += amount
                if horse_num == winning_horse.number:
                    winning_pool += amount

        if winning_pool > 0:
            # 計算賠率
            odds = (total_pool * 0.9) / winning_pool  # 抽取10%作為手續費

            # 發放獎金
            winners_text = ""
            for user_id, bets in self.race_system.bets.items():
                if winning_horse.number in bets:
                    user = self.bot.get_user(user_id)
                    bet_amount = bets[winning_horse.number]
                    winnings = int(bet_amount * odds)
                    
                    # 更新玩家金幣
                    currency = Currency(self.bot)
                    await currency.update_balance(user_id, winnings, user.name if user else str(user_id))
                    
                    winners_text += f"{user.mention if user else user_id} 贏得了 {winnings:,} Silva幣！\n"

            if winners_text:
                result_embed.add_field(name="🎉 獲獎者", value=winners_text, inline=False)
            result_embed.add_field(name="賠率", value=f"{odds:.2f}x", inline=False)

        await self.race_system.race_channel.send(embed=result_embed)
        self.race_system.is_race_active = False
        self.race_system.bets = {}
        
    @app_commands.command(name="horserace", description="在賽馬比賽中下注")
    @app_commands.describe(
        horse_number="要下注的馬匹號碼(1-5)",
        amount="下注金額(Silva幣)"
    )
    async def horserace(
        self,
        interaction: discord.Interaction,
        horse_number: int,
        amount: int
    ):
        """
        在賽馬比賽中下注
        參數:
            horse_number: 馬匹號碼
            amount: 下注金額
        """
        if not self.race_system.betting_open:
            await interaction.response.send_message("❌ 目前不是下注時間！", ephemeral=True)
            return

        if horse_number < 1 or horse_number > 5:
            await interaction.response.send_message("❌ 請輸入有效的馬匹號碼(1-5)！", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ 下注金額必須大於0！", ephemeral=True)
            return

        # 檢查玩家餘額
        currency = Currency(self.bot)
        balance = await currency.get_balance(interaction.user.id)
        
        if balance < amount:
            await interaction.response.send_message(
                f"❌ 餘額不足！你現在有 {balance:,} Silva幣，但你想下注 {amount:,} Silva幣",
                ephemeral=True
            )
            return

        # 扣除下注金額
        await currency.update_balance(interaction.user.id, -amount, interaction.user.name)
        
        # 記錄下注
        if self.race_system.place_bet(interaction.user.id, horse_number, amount):
            horse = next(h for h in self.race_system.horses if h.number == horse_number)
            await interaction.response.send_message(
                f"✅ 成功在 {horse.emoji} #{horse_number} {horse.name} 下注 {amount:,} Silva幣！",
                ephemeral=False
            )
        else:
            # 如果下注失敗，退還金額
            await currency.update_balance(interaction.user.id, amount, interaction.user.name)
            await interaction.response.send_message("❌ 下注失敗！", ephemeral=True)
            
    @app_commands.command(name="setracechannel", description="設定賽馬比賽頻道 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def set_race_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """
        設定賽馬比賽頻道
        參數:
            channel: 要設定的頻道，不提供則設定為當前頻道
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        # 如果沒有提供頻道，使用當前頻道
        target_channel = channel or interaction.channel
        
        # 更新配置
        from config import set_config_value
        set_config_value('race_channel', target_channel.id)
        
        # 更新賽馬系統的頻道
        self.race_system.race_channel = target_channel
        
        await interaction.response.send_message(
            f"✅ 已將賽馬比賽頻道設定為 {target_channel.mention}",
            ephemeral=False
        )

async def setup(bot):
    await bot.add_cog(HorseRaceCog(bot))