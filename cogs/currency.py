import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
from models.currency import Currency

class CurrencyCog(commands.Cog):
    """Silva幣系統指令"""

    def __init__(self, bot):
        self.bot = bot
        self.currency = Currency(bot)

    @app_commands.command(name="money", description="查看當前Silva幣餘額")
    async def check_balance(self, interaction: discord.Interaction):
        """查看當前Silva幣餘額"""
        user_id = interaction.user.id
        balance = await self.currency.get_balance(user_id)
        
        embed = discord.Embed(
            title="💰 Silva幣餘額查詢",
            color=discord.Color.gold()
        )
        embed.add_field(
            name=f"{interaction.user.name}的錢包", 
            value=f"**{balance:,}** Silva幣"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pay", description="轉帳給其他用戶")
    @app_commands.describe(recipient="要轉帳的對象", amount="轉帳金額")
    async def transfer_money(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        """轉帳給其他用戶"""
        if amount <= 0:
            await interaction.response.send_message("❌ 轉帳金額必須大於0！", ephemeral=True)
            return

        sender_balance = await self.currency.get_balance(interaction.user.id)
        if sender_balance < amount:
            await interaction.response.send_message("❌ 餘額不足！", ephemeral=True)
            return

        # 扣除發送者的金額
        await self.currency.update_balance(interaction.user.id, -amount, interaction.user.name)
        # 增加接收者的金額
        await self.currency.update_balance(recipient.id, amount, recipient.name)

        embed = discord.Embed(
            title="💸 轉帳成功！",
            color=discord.Color.green(),
            description=f"{interaction.user.mention} 轉給 {recipient.mention} **{amount:,}** Silva幣"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rich", description="顯示富豪榜")
    async def richest_users(self, interaction: discord.Interaction):
        """顯示富豪榜"""
        rich_list = await self.currency.get_top_balance(10)
        
        if not rich_list:
            await interaction.response.send_message("還沒有任何紀錄！")
            return

        embed = discord.Embed(
            title="🏆 Silva幣富豪榜",
            color=discord.Color.gold()
        )
        
        # 定義名次顯示格式
        rank_formats = {
            1: "🥇 第1名",
            2: "🥈 第2名",
            3: "🥉 第3名"
        }
        
        total_balance = 0
        total_users = 0
        
        for idx, (username, balance) in enumerate(rich_list, 1):
            # 對前三名使用特殊格式，其他使用數字
            rank_display = rank_formats.get(idx, f"第{idx}名")
            
            embed.add_field(
                name=rank_display, 
                value=f"{username}: **{balance:,}** Silva幣",
                inline=False
            )
            
            total_balance += balance
            total_users += 1
        
        # 添加總計資訊
        embed.set_footer(text=f"共有 {total_users} 位玩家擁有 Silva幣，總計 {total_balance:,} Silva幣")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="領取每日獎勵")
    async def daily_bonus(self, interaction: discord.Interaction):
        """領取每日獎勵"""
        user_id = interaction.user.id
        
        # 隨機獎勵金額
        bonus = random.randint(100, 1000)
        
        # 嘗試領取獎勵
        success, result = await self.currency.update_daily(user_id, interaction.user.name, bonus)
        
        if not success:
            # 如果失敗，result 是剩餘時間
            time_until_next = result
            hours, remainder = divmod(time_until_next.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            await interaction.response.send_message(
                f"❌ 每日獎勵冷卻中！\n下次可領取時間: **{hours}**小時**{minutes}**分鐘**{seconds}**秒",
                ephemeral=True
            )
            return
        
        # 如果成功，result 是新餘額
        new_balance = result
        
        embed = discord.Embed(
            title="🎁 每日獎勵",
            description=f"恭喜獲得 **{bonus}** Silva幣！",
            color=discord.Color.green()
        )
        embed.add_field(name="當前餘額", value=f"**{new_balance:,}** Silva幣")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_money", description="設定使用者的 Silva幣 數量 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def set_money(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """設定使用者的 Silva幣 數量 (管理員專用)"""
        try:
            # 計算需要增加或減少的金額
            current_balance = await self.currency.get_balance(user.id)
            delta_amount = amount - current_balance
            
            # 更新用戶餘額
            success = await self.currency.update_balance(user.id, delta_amount, user.name)
            
            if success:
                embed = discord.Embed(
                    title="💰 Silva幣設定成功",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="目標用戶", 
                    value=f"{user.mention}", 
                    inline=False
                )
                embed.add_field(
                    name="設定金額", 
                    value=f"**{amount:,}** Silva幣", 
                    inline=False
                )
                embed.add_field(
                    name="變動數量", 
                    value=f"**{delta_amount:+,}** Silva幣", 
                    inline=False
                )
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ 設定失敗",
                    description="無法設定該金額，請檢查數值是否正確",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ 發生錯誤",
                description=f"設定金額時發生錯誤：{str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="money_history", description="查看使用者的 Silva幣 使用紀錄 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def money_history(self, interaction: discord.Interaction, user: discord.Member, limit: int = 10):
        """查看使用者的 Silva幣 使用紀錄 (管理員專用)"""
        try:
            history = await self.currency.get_transaction_history(user.id, limit)
            
            if not history:
                embed = discord.Embed(
                    title="📜 交易紀錄",
                    description=f"{user.mention} 目前沒有任何交易紀錄",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title="📜 Silva幣 交易紀錄",
                description=f"{user.mention} 的最近 {limit} 筆交易",
                color=discord.Color.blue()
            )
            
            for i, (amount, balance_after, description, created_at) in enumerate(history, 1):
                # 將 timestamp 轉換為可讀格式
                if isinstance(created_at, str):
                    created_at = datetime.datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                
                embed.add_field(
                    name=f"#{i} {created_at.strftime('%Y-%m-%d %H:%M')}",
                    value=f"```變動: {amount:+,}\n餘額: {balance_after:,}\n說明: {description}```",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ 發生錯誤",
                description=f"獲取交易紀錄時發生錯誤：{str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(CurrencyCog(bot))