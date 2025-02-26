import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import json
import os

class RoleButton(Button):
    """身分組按鈕"""
    def __init__(self, role_id: int, role_name: str):
        super().__init__(
            label=role_name,
            style=discord.ButtonStyle.primary,
            custom_id=f"role_{role_id}"  # 確保 custom_id 是唯一的
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        """按鈕回調函數"""
        user = interaction.user
        role = interaction.guild.get_role(self.role_id)
        
        if role is None:
            await interaction.response.send_message("找不到該身分組!", ephemeral=True)
            return
            
        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f"已移除 {role.name} 身分組", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f"已新增 {role.name} 身分組", ephemeral=True)

class RoleButtonView(View):
    """身分組按鈕視圖"""
    def __init__(self, roles):
        super().__init__(timeout=None)  # 設置 timeout=None 使按鈕持久化
        self.roles = roles  # 保存角色信息
        for role_id, role_name in roles:
            button = RoleButton(role_id, role_name)
            self.add_item(button)

class RolesCog(commands.Cog):
    """身分組管理指令"""

    def __init__(self, bot):
        self.bot = bot
        self.persistent_views = {}  # 存儲所有持久化視圖的字典
        self.bot.loop.create_task(self.load_persistent_views())

    async def load_persistent_views(self):
        """載入持久化按鈕視圖"""
        await self.bot.wait_until_ready()
        
        try:
            for guild in self.bot.guilds:
                try:
                    # 讀取該伺服器的持久化按鈕配置
                    file_path = f'role_buttons_{guild.id}.json'
                    if not os.path.exists(file_path):
                        continue
                        
                    with open(file_path, 'r', encoding='utf8') as f:
                        role_data = json.load(f)
                        
                    for channel_id, roles in role_data.items():
                        view = RoleButtonView(roles)
                        self.persistent_views[int(channel_id)] = view
                        self.bot.add_view(view)
                        
                    print(f"已載入伺服器 {guild.name} 的角色按鈕")
                except FileNotFoundError:
                    continue  # 如果檔案不存在，跳過該伺服器
                except Exception as e:
                    print(f"加載伺服器 {guild.id} 的持久化按鈕時出錯: {e}")
        except Exception as e:
            print(f"載入持久化視圖時發生錯誤: {e}")

    @app_commands.command(name="role", description="設置角色選擇按鈕")
    @app_commands.default_permissions(administrator=True)
    async def role(self, interaction: discord.Interaction, roles: str):
        """
        設置角色選擇按鈕
        參數:
            roles: 角色ID列表，格式為 "角色名稱1:角色ID1/角色名稱2:角色ID2"
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令!", ephemeral=True)
            return

        try:
            # 解析角色參數
            role_pairs = []
            role_inputs = roles.split('/')
            
            for role_input in role_inputs:
                name, role_id = role_input.split(':')
                role_pairs.append((int(role_id), name))

            # 創建視圖
            view = RoleButtonView(role_pairs)
            
            # 發送消息並保存視圖
            await interaction.response.send_message("請點擊下方按鈕來選擇身分組：", view=view)
            
            # 獲取發送的消息
            message = await interaction.original_response()
            
            # 保存該頻道的角色按鈕配置
            file_path = f'role_buttons_{interaction.guild_id}.json'
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf8') as f:
                        role_data = json.load(f)
                else:
                    role_data = {}
            except:
                role_data = {}
                
            role_data[str(message.channel.id)] = role_pairs
            
            with open(file_path, 'w', encoding='utf8') as f:
                json.dump(role_data, f, ensure_ascii=False, indent=4)
                
            # 將視圖添加到持久化存儲中
            self.persistent_views[message.channel.id] = view
            self.bot.add_view(view)
            
        except Exception as e:
            await interaction.response.send_message(
                f"設置失敗! 請確認輸入格式正確\n格式範例: 管理員:123456789/成員:987654321\n錯誤: {str(e)}", 
                ephemeral=True
            )
            print(f"Error: {e}")

async def setup(bot):
    await bot.add_cog(RolesCog(bot))