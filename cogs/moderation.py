import discord
from discord.ext import commands
from discord import app_commands
import datetime

# 定義時間選項的列舉
time_choices = [
    app_commands.Choice(name="1分鐘", value="60"),
    app_commands.Choice(name="5分鐘", value="300"),
    app_commands.Choice(name="10分鐘", value="600"),
    app_commands.Choice(name="1小時", value="3600"),
    app_commands.Choice(name="1天", value="86400"),
    app_commands.Choice(name="1週", value="604800"),
]

class ModerationCog(commands.Cog):
    """管理員指令"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shutup", description="禁言指定用戶")
    @app_commands.describe(
        member="要禁言的成員",
        duration="禁言時間"
    )
    @app_commands.choices(duration=time_choices)
    async def shutup(
        self,
        interaction: discord.Interaction, 
        member: discord.Member,
        duration: app_commands.Choice[str]
    ):
        """
        禁言指定用戶
        參數:
            member: 要禁言的成員
            duration: 禁言時間
        """
        # 檢查使用者權限
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        # 檢查目標用戶是否可以被禁言
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("你不能禁言權限比你高或相同的成員！", ephemeral=True)
            return
            
        if member.guild_permissions.administrator:
            await interaction.response.send_message("你不能禁言管理員！", ephemeral=True)
            return

        try:
            # 轉換時間
            seconds = int(duration.value)
            timeout_duration = datetime.timedelta(seconds=seconds)
            
            # 執行禁言
            await member.timeout(timeout_duration, reason=f"被 {interaction.user} 禁言")
            
            # 發送確認訊息
            await interaction.response.send_message(
                f"已將 {member.mention} 禁言 {duration.name}",
                ephemeral=False
            )
        except Exception as e:
            await interaction.response.send_message(
                f"禁言失敗！可能是因為：\n1. 目標用戶權限較高\n2. 機器人權限不足\n錯誤訊息: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="unmute", description="解除指定用戶的禁言")
    @app_commands.describe(member="要解除禁言的成員")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        """
        解除指定用戶的禁言
        參數:
            member: 要解除禁言的成員
        """
        # 檢查使用者權限
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return

        try:
            await member.timeout(None, reason=f"被 {interaction.user} 解除禁言")
            await interaction.response.send_message(f"已解除 {member.mention} 的禁言狀態", ephemeral=False)
        except Exception as e:
            await interaction.response.send_message(f"解除禁言失敗！錯誤訊息: {str(e)}", ephemeral=True)

    # 這裡可以添加其他管理類指令，如清除訊息、踢出用戶等

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))