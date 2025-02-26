import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import random
import asyncio
from models.games import Deck, Hand
from models.currency import Currency

class BlackjackView(discord.ui.View):
    """21點遊戲視圖"""
    def __init__(self, game, bet: int):
        super().__init__(timeout=180)
        self.game = game
        self.bet = bet
        self.ended = False
        
    @discord.ui.button(label="抽牌", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """抽牌按鈕"""
        if interaction.user.id != self.game.player_id:
            return
        
        card = self.game.deck.draw()
        self.game.player_hand.add_card(card)
        
        if self.game.player_hand.get_value() > 21:
            self.ended = True
            await self.end_game(interaction, "爆牌")
            return
            
        await self.update_game_message(interaction)
        
    @discord.ui.button(label="停牌", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        """停牌按鈕"""
        if interaction.user.id != self.game.player_id:
            return
            
        self.ended = True
        
        # 莊家抽牌
        while self.game.dealer_hand.get_value() < 17:
            card = self.game.deck.draw()
            self.game.dealer_hand.add_card(card)
            
        await self.end_game(interaction)
        
    async def update_game_message(self, interaction: discord.Interaction):
        """更新遊戲訊息"""
        embed = self.game.create_game_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
    async def end_game(self, interaction: discord.Interaction, result: str = None):
        """結束遊戲"""
        player_value = self.game.player_hand.get_value()
        dealer_value = self.game.dealer_hand.get_value()
        
        if result == "爆牌":
            outcome = "玩家爆牌，莊家勝!"
            win_amount = -self.bet
        elif dealer_value > 21:
            outcome = "莊家爆牌，玩家勝!"
            win_amount = self.bet  # 贏得下注金額
        elif player_value > dealer_value:
            outcome = "玩家勝!"
            win_amount = self.bet  # 贏得下注金額
        elif player_value < dealer_value:
            outcome = "莊家勝!"
            win_amount = -self.bet
        else:
            outcome = "平手!"
            win_amount = 0  # 平手不變
            
        # 更新玩家金幣
        currency = Currency(self.game.bot)
        
        if win_amount != -self.bet:  # 如果不是輸掉全部下注
            await currency.update_balance(self.game.player_id, win_amount, self.game.player_name)
            
        # 獲取更新後的餘額
        new_balance = await currency.get_balance(self.game.player_id)
        
        embed = discord.Embed(
            title="Blackjack - 遊戲結束",
            description=f"結果: {outcome}",
            color=discord.Color.blue()
        )
        embed.add_field(name=f"玩家 ({player_value}點)", value=str(self.game.player_hand), inline=False)
        embed.add_field(name=f"莊家 ({dealer_value}點)", value=str(self.game.dealer_hand), inline=False)
        
        # 處理獲勝或平手的情況
        if win_amount > 0:
            result_text = f"贏得: {win_amount:,} Silva幣"
        elif win_amount < 0:
            result_text = f"損失: {abs(win_amount):,} Silva幣"
        else:
            result_text = "平手，不獲得也不損失Silva幣"
            
        embed.add_field(
            name="下注結算", 
            value=f"原下注: {self.bet:,} Silva幣\n"
                  f"{result_text}\n"
                  f"當前餘額: {new_balance:,} Silva幣",
            inline=False
        )
        
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)

class Blackjack:
    """21點遊戲模型"""
    def __init__(self, bot, player_id: int, player_name: str):
        self.bot = bot
        self.player_id = player_id
        self.player_name = player_name
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        
    def deal_initial_cards(self):
        """發初始牌"""
        for _ in range(2):
            self.player_hand.add_card(self.deck.draw())
        self.dealer_hand.add_card(self.deck.draw())
        
    def create_game_embed(self) -> discord.Embed:
        """創建遊戲嵌入訊息"""
        embed = discord.Embed(
            title="Blackjack",
            color=discord.Color.blue()
        )
        
        player_value = self.player_hand.get_value()
        embed.add_field(
            name=f"玩家 ({player_value}點)", 
            value=str(self.player_hand),
            inline=False
        )
        
        # 只顯示莊家的第一張牌
        embed.add_field(
            name="莊家", 
            value=f"{self.dealer_hand.cards[0]} ?",
            inline=False
        )
        
        return embed

class BlackjackCog(commands.Cog):
    """21點遊戲指令"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackjack", description="開始21點遊戲")
    @app_commands.describe(bet="下注金額 (Silva幣)")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        """
        開始21點遊戲
        參數:
            bet: 下注金額
        """
        # 檢查下注金額
        if bet <= 0:
            await interaction.response.send_message("❌ 下注金額必須大於0！", ephemeral=True)
            return
        
        # 檢查玩家餘額
        currency = Currency(self.bot)
        balance = await currency.get_balance(interaction.user.id)
        
        if balance < bet:
            await interaction.response.send_message(
                f"❌ 餘額不足！你現在有 {balance:,} Silva幣，但你想下注 {bet:,} Silva幣", 
                ephemeral=True
            )
            return
        
        # 先扣除下注金額
        await currency.update_balance(interaction.user.id, -bet, interaction.user.name)
            
        # 建立遊戲
        game = Blackjack(self.bot, interaction.user.id, interaction.user.name)
        game.deal_initial_cards()
        
        # 創建遊戲視圖
        view = BlackjackView(game, bet)
        embed = game.create_game_embed()
        
        # 添加下注金額資訊到 embed
        embed.add_field(
            name="下注金額", 
            value=f"{bet:,} Silva幣", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # 等待遊戲結束或超時
        await view.wait()
        if not view.ended:
            # 如果遊戲超時，退還下注金額
            await currency.update_balance(interaction.user.id, bet, interaction.user.name)
            
            embed = discord.Embed(
                title="Blackjack - 遊戲超時",
                description="遊戲已取消，已退還下注金額。",
                color=discord.Color.red()
            )
            for child in view.children:
                child.disabled = True
                
            await interaction.edit_original_response(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(BlackjackCog(bot))