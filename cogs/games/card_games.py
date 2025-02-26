import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import random
import asyncio

class HighCardButton(Button):
    """比大小按鈕"""
    def __init__(self, user: discord.Member):
        super().__init__(
            label=f"{user.display_name} 抽牌",
            style=discord.ButtonStyle.primary,
            custom_id=f"highcard_{user.id}"
        )
        self.user = user
        self.number = None

    async def callback(self, interaction: discord.Interaction):
        """按鈕回調函數"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("這不是你的按鈕！", ephemeral=True)
            return

        if self.number is not None:
            await interaction.response.send_message("你已經抽過牌了！", ephemeral=True)
            return

        self.number = random.randint(1, 13)
        self.disabled = True
        self.label = f"{self.user.display_name}: {self.number}點"
        
        # 檢查是否雙方都已抽牌
        other_button = None
        for child in self.view.children:
            if isinstance(child, HighCardButton) and child != self:
                other_button = child
                break

        if other_button and other_button.number is not None:
            # 兩位玩家都抽完牌，決定勝負
            embed = self.view.message.embeds[0]
            
            # 更新embed的描述來顯示結果
            if self.number > other_button.number:
                winner = self.user
                embed.description = f"🎉 獲勝者是 {winner.mention}!"
            elif self.number < other_button.number:
                winner = other_button.user
                embed.description = f"🎉 獲勝者是 {winner.mention}!"
            else:
                embed.description = "平手！"

            embed.add_field(name=f"{self.user.display_name}", value=f"{self.number}點", inline=True)
            embed.add_field(name=f"{other_button.user.display_name}", value=f"{other_button.number}點", inline=True)
            
            await self.view.message.edit(embed=embed, view=self.view)
            self.view.stop()
        else:
            await interaction.message.edit(view=self.view)

        await interaction.response.defer()

class HighCardView(View):
    """比大小視圖"""
    def __init__(self, user1: discord.Member, user2: discord.Member):
        super().__init__(timeout=60)  # 60秒超時
        self.user1 = user1
        self.user2 = user2
        self.message = None
        
        # 添加兩個玩家的按鈕
        self.add_item(HighCardButton(user1))
        self.add_item(HighCardButton(user2))

    async def on_timeout(self):
        """超時處理"""
        # 檢查是否有人還沒抽牌
        not_drawn = []
        for child in self.children:
            if isinstance(child, HighCardButton) and child.number is None:
                not_drawn.append(child.user.display_name)

        # 更新embed
        if self.message:
            embed = self.message.embeds[0]
            if not_drawn:
                embed.description = f"遊戲結束！以下玩家未及時抽牌：{', '.join(not_drawn)}"
            else:
                embed.description = "遊戲結束！"
            
            for child in self.children:
                child.disabled = True
            
            await self.message.edit(embed=embed, view=self)

class RPSButton(Button):
    """剪刀石頭布按鈕"""
    def __init__(self, choice: str, emoji: str):
        super().__init__(
            label=choice,
            emoji=emoji,
            style=discord.ButtonStyle.primary,
            custom_id=f"rps_{choice}"
        )

class RPSView(View):
    """剪刀石頭布視圖"""
    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=60)
        self.player1 = player1
        self.player2 = player2
        self.choices = {}
        self.message = None
        
        # 添加三個選擇按鈕
        choices = [
            ("剪刀", "✂️"),
            ("石頭", "🪨"),
            ("布", "📄")
        ]
        
        for choice, emoji in choices:
            button = RPSButton(choice, emoji)
            button.callback = self.create_button_callback(choice)
            self.add_item(button)

    def create_button_callback(self, choice: str):
        """創建按鈕回調函數"""
        async def button_callback(interaction: discord.Interaction):
            # 檢查是否為遊戲參與者
            if interaction.user.id not in [self.player1.id, self.player2.id]:
                await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
                return

            # 檢查是否已經做出選擇
            if interaction.user.id in self.choices:
                await interaction.response.send_message("你已經做出選擇了！", ephemeral=True)
                return

            # 記錄選擇
            self.choices[interaction.user.id] = choice
            await interaction.response.send_message(f"你選擇了 {choice}！", ephemeral=True)

            # 更新狀態顯示
            embed = discord.Embed(
                title="🎮 剪刀石頭布！",
                description="等待玩家做出選擇...",
                color=discord.Color.blue()
            )

            status = []
            for player in [self.player1, self.player2]:
                if player.id in self.choices:
                    status.append(f"{player.mention} ✅")
                else:
                    status.append(f"{player.mention} ⏳")
            embed.add_field(name="玩家狀態", value="\n".join(status))

            await self.message.edit(embed=embed)

            # 如果兩位玩家都已選擇，顯示結果
            if len(self.choices) == 2:
                await self.show_result()

        return button_callback

    def determine_winner(self):
        """判斷獲勝者"""
        choice1 = self.choices[self.player1.id]
        choice2 = self.choices[self.player2.id]

        if choice1 == choice2:
            return None  # 平手

        winning_combinations = {
            "剪刀": "布",
            "石頭": "剪刀",
            "布": "石頭"
        }

        if winning_combinations[choice1] == choice2:
            return self.player1
        return self.player2

    async def show_result(self):
        """顯示結果"""
        choice1 = self.choices[self.player1.id]
        choice2 = self.choices[self.player2.id]
        winner = self.determine_winner()

        embed = discord.Embed(
            title="🎮 剪刀石頭布！",
            color=discord.Color.green()
        )

        if winner is None:
            embed.description = "**結果：平手！**"
        else:
            embed.description = f"**🎉 獲勝者是 {winner.mention}！**"

        embed.add_field(
            name=f"{self.player1.display_name} 出了",
            value=f"{self.choices[self.player1.id]}",
            inline=True
        )
        embed.add_field(
            name=f"{self.player2.display_name} 出了",
            value=f"{self.choices[self.player2.id]}",
            inline=True
        )

        # 禁用所有按鈕
        for item in self.children:
            item.disabled = True

        await self.message.edit(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        """超時處理"""
        if not self.message:
            return

        # 檢查誰還沒出拳
        not_played = []
        if self.player1.id not in self.choices:
            not_played.append(self.player1.display_name)
        if self.player2.id not in self.choices:
            not_played.append(self.player2.display_name)

        embed = discord.Embed(
            title="🎮 剪刀石頭布！",
            description=f"遊戲結束！以下玩家未及時做出選擇：{', '.join(not_played)}",
            color=discord.Color.red()
        )

        # 顯示已經做出的選擇
        for player_id, choice in self.choices.items():
            player = self.player1 if player_id == self.player1.id else self.player2
            embed.add_field(
                name=f"{player.display_name} 出了",
                value=choice,
                inline=True
            )

        # 禁用所有按鈕
        for item in self.children:
            item.disabled = True

        await self.message.edit(embed=embed, view=self)

class CardGamesCog(commands.Cog):
    """卡牌遊戲指令"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="highcards", description="與其他玩家進行比大小遊戲")
    @app_commands.describe(opponent="要挑戰的對手")
    async def highcards(self, interaction: discord.Interaction, opponent: discord.Member):
        """
        開始一個比大小遊戲
        參數:
            opponent: 要挑戰的對手
        """
        # 檢查是否正在挑戰自己
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("你不能跟自己比大小！", ephemeral=True)
            return

        # 檢查對手是否是機器人
        if opponent.bot:
            await interaction.response.send_message("你不能跟機器人比大小！", ephemeral=True)
            return

        # 創建遊戲視圖
        view = HighCardView(interaction.user, opponent)
        
        # 創建 embed 訊息
        embed = discord.Embed(
            title="🎲 比大小遊戲",
            description=f"{interaction.user.mention} VS {opponent.mention}\n請雙方點擊下方按鈕抽牌！",
            color=discord.Color.blue()
        )
        embed.set_footer(text="遊戲將在60秒後結束")

        # 發送遊戲訊息
        await interaction.response.send_message(embed=embed, view=view)
        
        # 保存訊息引用以供更新
        original_message = await interaction.original_response()
        view.message = original_message

    @app_commands.command(name="paperblabla", description="開始一局剪刀石頭布")
    @app_commands.describe(opponent="要挑戰的對手")
    async def rps(self, interaction: discord.Interaction, opponent: discord.Member):
        """
        開始一局剪刀石頭布
        參數:
            opponent: 要挑戰的對手
        """
        # 檢查是否挑戰自己
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("你不能和自己玩！", ephemeral=True)
            return

        # 檢查是否挑戰機器人
        if opponent.bot:
            await interaction.response.send_message("你不能和機器人玩！", ephemeral=True)
            return

        # 創建遊戲視圖
        view = RPSView(interaction.user, opponent)

        # 創建初始 embed
        embed = discord.Embed(
            title="🎮 剪刀石頭布！",
            description=f"{interaction.user.mention} VS {opponent.mention}\n請選擇要出的拳！",
            color=discord.Color.blue()
        )
        embed.set_footer(text="遊戲將在60秒後結束")

        # 發送遊戲訊息
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(CardGamesCog(bot))