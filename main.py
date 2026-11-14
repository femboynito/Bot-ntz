import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading

# --- Flask pra manter online no Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot online!"

def rodar_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=rodar_flask, daemon=True).start()

# --- Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Salva os formulários criados: { custom_id : {titulo, descricao} }
formularios = {}

# --- Modal pra RESPONDER o formulário (quando o usuário clica no botão) ---
class ModalResponder(discord.ui.Modal, title="Responder Formulário"):
    resposta1 = discord.ui.TextInput(label="Sua resposta", placeholder="Digite aqui...", style=discord.TextStyle.paragraph, required=True, max_length=1000)

    def __init__(self, titulo_form):
        super().__init__(title=f"Responder: {titulo_form[:40]}")
        self.titulo_form = titulo_form

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Sua resposta para **{self.titulo_form}** foi enviada!\n\n**Resposta:** {self.resposta1.value}", ephemeral=True)

# --- View com o botão ---
class ViewResponder(discord.ui.View):
    def __init__(self, nome_botao, titulo_form):
        super().__init__(timeout=None)
        self.titulo_form = titulo_form
        # AQUI ESTAVA O ERRO - agora cria o botão do zero
        self.botao = discord.ui.Button(label=nome_botao, style=discord.ButtonStyle.primary, custom_id=f"responder_{titulo_form}")
        self.botao.callback = self.clicou_botao
        self.add_item(self.botao)

    async def clicou_botao(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalResponder(self.titulo_form))

# --- Modal pra CRIAR o painel ---
class ModalCriarPainel(discord.ui.Modal, title="Criar Painel Formulario"):
    titulo = discord.ui.TextInput(label="Titulo do Formulario", placeholder="Prova staff", required=True, max_length=100)
    descricao = discord.ui.TextInput(label="Descricao", placeholder="Seja staff...", style=discord.TextStyle.paragraph, required=True, max_length=1000)
    imagem = discord.ui.TextInput(label="Imagem (link) - pode deixar vazio", placeholder="https://...", required=False, max_length=200)
    nome_botao = discord.ui.TextInput(label="Nome do botao", placeholder="Responder Formulario", required=True, max_length=80)

    async def on_submit(self, interaction: discord.Interaction):
        titulo_txt = self.titulo.value
        descricao_txt = self.descricao.value
        imagem_txt = self.imagem.value
        nome_botao_txt = self.nome_botao.value

        embed = discord.Embed(title=titulo_txt, description=descricao_txt, color=discord.Color.blurple())
        if imagem_txt and imagem_txt.startswith("http"):
            embed.set_image(url=imagem_txt)

        view = ViewResponder(nome_botao_txt, titulo_txt)
        formularios[titulo_txt] = {"titulo": titulo_txt, "descricao": descricao_txt}

        await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comandos")
    except Exception as e:
        print(f"Erro sync: {e}")

@bot.tree.command(name="criar_painel", description="Criar painel de formulário")
async def criar_painel(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalCriarPainel())

TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
