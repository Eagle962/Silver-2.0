import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import random
import asyncio
import datetime
from models.currency import Currency

class RussianRouletteButton(Button):
    """俄羅斯輪盤按鈕"""
    def __init__(self, label: str, position: int):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.gray,
            custom_id=str(position)
        )
        
class RussianRouletteView(discord.ui.View):
    """俄羅斯輪盤視圖"""
    def __init__(self, death_positions: list, bet_amount: int, user_id: int):
        super().__init__(timeout=30)
        self.death_positions = death_positions
        self.bet_amount = bet_amount
        self.user_id = user_id
        self.ended = False
        
    @discord.ui.button(label="1", style=discord.ButtonStyle.gray)
    async def button_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_position(interaction, 0)

    @discord.ui.button(label="2", style=discord.ButtonStyle.gray) 
    async def button_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_position(interaction, 1)

    @discord.ui.button(label="3", style=discord.ButtonStyle.gray)
    async def button_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_position(interaction, 2)

    @discord.ui.button(label="4", style=discord.ButtonStyle.gray)
    async def button_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_position(interaction, 3)

    @discord.ui.button(label="5", style=discord.ButtonStyle.gray)
    async def button_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_position(interaction, 4)

    @discord.ui.button(label="6", style=discord.ButtonStyle.gray)
    async def button_6(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.check_position(interaction, 5)

    async def check_position(self, interaction: discord.Interaction, position: int):
        """檢查選擇的位置"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的遊戲!", ephemeral=True)
            return

        self.ended = True
        currency = Currency(interaction.client)

        if position in self.death_positions:
            # 輸了
            embed = discord.Embed(
                title="💥 砰!",
                description=f"你死了! 失去 {self.bet_amount:,} Silva幣",
                color=discord.Color.red()
            )
            try:
                # 直接設置60秒的禁言
                seconds = 60
                timeout_duration = datetime.timedelta(seconds=seconds)
                await interaction.user.timeout(timeout_duration, reason=f"俄羅斯輪盤遊戲懲罰")
                embed.description += f"\n已被禁言 60 秒"
                
            except Exception as e:
                embed.description += "\n(錯誤：禁言失敗)"
                print(f"禁言錯誤: {str(e)}")
        else:
            # 贏了
            bullets = len(self.death_positions)
            multiplier = 1 + (bullets / 12)  
            win_amount = int(self.bet_amount * multiplier)
            gain = win_amount - self.bet_amount
            
            # 修正: 需要返還原下注加上獎金，win_amount是總收入
            await currency.update_balance(self.user_id, win_amount, str(interaction.user))
            
            embed = discord.Embed(
                title="🎉 你活下來了!",
                description=f"恭喜獲得 {gain:,} Silva幣\n總計: {win_amount:,} Silva幣",
                color=discord.Color.green()
            )

        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)

class RussianCog(commands.Cog):
    """俄羅斯輪盤遊戲指令"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="russian", description="開始俄羅斯輪盤遊戲")
    @app_commands.describe(
        bullets="子彈數量 (1-5顆)",
        bet="下注金額 (最少100)"
    )
    async def russian(
        self, 
        interaction: discord.Interaction, 
        bullets: app_commands.Range[int, 1, 5], 
        bet: app_commands.Range[int, 100, None]
    ):
        """
        開始俄羅斯輪盤遊戲
        參數:
            bullets: 子彈數量
            bet: 下注金額
        """
        # 檢查下注金額
        if bet <= 0:
            await interaction.response.send_message("❌ 下注金額必須大於0！", ephemeral=True)
            return
        
        # 檢查玩家餘額
        currency = Currency(self.bot)
        balance = await currency.get_balance(interaction.user.id)
        
        if balance > 1000000:
            await interaction.response.send_message(
                f"你錢有點多 這是給窮人的遊戲", 
                ephemeral=True
            )
            return
            
        if balance < bet:
            await interaction.response.send_message(
                f"❌ 餘額不足！你現在有 {balance:,} Silva幣，但你想下注 {bet:,} Silva幣", 
                ephemeral=True
            )
            return

        # 扣除下注金額
        await currency.update_balance(interaction.user.id, -bet, str(interaction.user))
        
        # 隨機選擇死亡位置
        positions = random.sample(range(6), bullets)
        multiplier = 1 + (bullets / 6)

        embed = discord.Embed(
            title="🎲 俄羅斯輪盤",
            description=f"規則:\n"
                        f"• 有6個位置，裝填了 {bullets} 顆子彈\n"
                        f"• 選中子彈將被禁言1分鐘\n"
                        f"• 活下來可獲得 {bet:,} × {multiplier:.2f} = {int(bet * multiplier):,} Silva幣\n"
                        f"• 下注金額: {bet:,} Silva幣\n\n"
                        f"請選擇下方按鈕 1-6",
            color=discord.Color.red()
        )
        
        view = RussianRouletteView(positions, bet, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)
        
        # 等待遊戲結束或超時
        await view.wait()
        if not view.ended:
            # 如果遊戲超時，退還下注金額
            await currency.update_balance(interaction.user.id, bet, interaction.user.name)
            
            embed = discord.Embed(
                title="🎲 俄羅斯輪盤 - 遊戲超時",
                description="遊戲已取消，已退還下注金額。",
                color=discord.Color.red()
            )
            for child in view.children:
                child.disabled = True
            await interaction.edit_original_response(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(RussianCog(bot))