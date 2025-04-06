import discord
from discord.ext import commands
from discord import app_commands
from models.currency import Currency
from utils.database import get_db_connection, execute_query, table_exists

class StarterPackageCog(commands.Cog):
    """新手禮包系統指令"""

    def __init__(self, bot):
        self.bot = bot
        self.currency = Currency(bot)
        self.db_name = "starter_package"

    async def setup_database(self):
        """初始化資料庫表格"""
        conn = await get_db_connection(self.db_name)
        cursor = await conn.cursor()
        
        # 創建新手禮包領取記錄表
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS starter_package_claims (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        await conn.commit()

    async def has_claimed_package(self, user_id: int) -> bool:
        """檢查用戶是否已領取過新手禮包"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = 'SELECT user_id FROM starter_package_claims WHERE user_id = ?'
        result = await execute_query(self.db_name, query, (user_id,), 'one')
        
        return result is not None
        
    async def record_claim(self, user_id: int, username: str):
        """記錄用戶已領取新手禮包"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = 'INSERT INTO starter_package_claims (user_id, username) VALUES (?, ?)'
        await execute_query(self.db_name, query, (user_id, username))

    @app_commands.command(name="ineedmoney", description="領取新手投資禮包 (50,000 Silva幣，每人限領一次)")
    async def starter_package(self, interaction: discord.Interaction):
        """領取新手投資禮包"""
        user_id = interaction.user.id
        username = interaction.user.name
        
        # 檢查是否已領取過
        if await self.has_claimed_package(user_id):
            embed = discord.Embed(
                title="❌ 無法領取新手禮包",
                description="你已經領取過新手投資禮包了！每個帳號只能領取一次。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 發放獎勵
        starter_amount = 50000
        await self.currency.update_balance(user_id, starter_amount, username)
        
        # 記錄已領取
        await self.record_claim(user_id, username)
        
        # 獲取更新後的餘額
        new_balance = await self.currency.get_balance(user_id)
        
        # 創建成功訊息
        embed = discord.Embed(
            title="💰 新手投資禮包",
            description=f"恭喜 {interaction.user.mention} 成功領取新手投資禮包！",
            color=discord.Color.green()
        )
        embed.add_field(name="獲得金額", value=f"**{starter_amount:,}** Silva幣", inline=False)
        embed.add_field(name="目前餘額", value=f"**{new_balance:,}** Silva幣", inline=False)
        embed.add_field(
            name="小提示", 
            value="你可以使用這筆資金開始你的投資之旅！\n"
                 "嘗試參與賽馬比賽、21點或投資股票來增加你的財富。\n"
                 "輸入 `/money` 隨時查看你的餘額。",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StarterPackageCog(bot))