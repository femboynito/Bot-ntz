from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run, daemon=True).start()

import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
forms = {}
CARGOS_STAFF = ["Dono", "Vice Dono", "Gerente"]

def tem_cargo_staff(member: discord.Member):
    for r in member.roles:
        if r.name in CARGOS_STAFF:
            return True
    return member.guild_permissions.administrator

class ModalCriarPainel(discord.ui.Modal, title="Criar Painel Formulario"):
    titulo = discord.ui.TextInput(label="Titulo do Formulario", placeholder="Ex: Prova final staff", max_length=100)
    descricao = discord.ui.TextInput(label="Descricao", placeholder="Descreva o formulario...", style=discord.TextStyle.paragraph, max_length=1000)
    imagem = discord.ui.TextInput(label="Imagem (link) - pode deixar vazio", required=False, placeholder="https://...")
    nome_botao = discord.ui.TextInput(label="Nome do botao", placeholder="Ex: Candidatar-se", max_length=80, default="Responder Formulario")
    def __init__(self, canal_publicar, canal_log, cargo_aprovado, cargo_reprovado):
        super().__init__()
        self.canal_publicar = canal_publicar
        self.canal_log = canal_log
        self.cargo_aprovado = cargo_aprovado
        self.cargo_reprovado = cargo_reprovado
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.titulo.value, description=self.descricao.value, color=0x2b2d31)
        if self.imagem.value:
            try:
                embed.set_image(url=self.imagem.value)
            except:
                pass
        view = ViewResponder()
        msg = await self.canal_publicar.send(embed=embed, view=view)
        forms[str(msg.id)] = {
            "titulo": self.titulo.value,
            "descricao": self.descricao.value,
            "imagem": self.imagem.value,
            "nome_botao": self.nome_botao.value,
            "canal_log_id": self.canal_log.id,
            "cargo_aprovado_id": self.cargo_aprovado.id if self.cargo_aprovado else None,
            "cargo_reprovado_id": self.cargo_reprovado.id if self.cargo_reprovado else None,
            "perguntas": [],
            "canal_publicar_id": self.canal_publicar.id
        }
        view2 = ViewResponder(nome_botao=self.nome_botao.value)
        await msg.edit(view=view2)
        texto = f"✅ Painel criado em {self.canal_publicar.mention}!\nID do painel: `{msg.id}`\nAgora adicione perguntas com /adicionar-pergunta"
        await interaction.response.send_message(texto, ephemeral=True)

class ViewResponder(discord.ui.View):
    def __init__(self, nome_botao="Responder Formulario"):
        super().__init__(timeout=None)
        self.botao.label = nome_botao
    @discord.ui.button(label="Responder Formulario", style=discord.ButtonStyle.primary, custom_id="responder_form")
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        form = forms.get(str(interaction.message.id))
        if not form:
            return await interaction.response.send_message("Formulario nao encontrado.", ephemeral=True)
        if not form["perguntas"]:
            return await interaction.response.send_message("Esse formulario ainda nao tem perguntas.", ephemeral=True)
        modal = ModalResponder(form, interaction.message.id)
        await interaction.response.send_modal(modal)

class ModalResponder(discord.ui.Modal):
    def __init__(self, form, painel_id):
        super().__init__(title=form["titulo"][:45])
        self.form = form
        self.painel_id = painel_id
        self.inputs = []
        for pergunta in form["perguntas"][:5]:
            inp = discord.ui.TextInput(label=pergunta[:45], placeholder="Digite sua resposta...", style=discord.TextStyle.paragraph, max_length=1000, required=True)
            self.add_item(inp)
            self.inputs.append(inp)
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        form = self.form
        canal_log = guild.get_channel(form["canal_log_id"])
        desc = f"**Candidatura de:** {interaction.user.mention} (`{interaction.user.id}`)\n\n"
        for inp, perg in zip(self.inputs, form["perguntas"]):
            desc += f"**{perg}**\n{inp.value}\n\n"
        embed = discord.Embed(title=f"{form['titulo']} - Nova Candidatura", description=desc, color=0xfee75c)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        view = ViewDecisao(painel_id=self.painel_id, candidato_id=interaction.user.id, respostas=desc)
        await canal_log.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Sua candidatura foi enviada!", ephemeral=True)

class ModalDecisao(discord.ui.Modal):
    def __init__(self, aprovado: bool, painel_id, candidato_id, respostas):
        titulo = "Aprovada" if aprovado else "Reprovada"
        super().__init__(title=titulo)
        self.aprovado = aprovado
        self.painel_id = painel_id
        self.candidato_id = candidato_id
        self.respostas = respostas
        self.motivo = discord.ui.TextInput(label="Motivo (publico)", placeholder="Vai para o candidato tambem", style=discord.TextStyle.paragraph, max_length=500)
        self.nota = discord.ui.TextInput(label="Nota Privada (so staff ve)", placeholder="So aparece no log da staff", style=discord.TextStyle.paragraph, max_length=500, required=False)
        self.add_item(self.motivo)
        self.add_item(self.nota)
    async def on_submit(self, interaction: discord.Interaction):
        if not tem_cargo_staff(interaction.user):
            return await interaction.response.send_message("❌ So Dono / Vice Dono / Gerente pode decidir.", ephemeral=True)
        form = forms.get(str(self.painel_id))
        titulo = form["titulo"] if form else "Formulario"
        guild = interaction.guild
        candidato = guild.get_member(self.candidato_id)
        if not candidato:
            candidato = await guild.fetch_member(self.candidato_id)
        decisao_txt = "Aprovada" if self.aprovado else "Reprovada"
        cor = 0x57f287 if self.aprovado else 0xed4245
        if form:
            cargo_id = form["cargo_aprovado_id"] if self.aprovado else form["cargo_reprovado_id"]
            if cargo_id and candidato:
                cargo = guild.get_role(cargo_id)
                if cargo:
                    try:
                        await candidato.add_roles(cargo)
                    except:
                        pass
        embed_log = discord.Embed(title=f"{titulo} - Candidatura {decisao_txt}", description=self.respostas, color=cor)
        embed_log.add_field(name="Decisao", value=decisao_txt, inline=True)
        embed_log.add_field(name="Decidido Por", value=interaction.user.mention, inline=True)
        embed_log.add_field(name="Motivo", value=self.motivo.value, inline=False)
        nota_txt = self.nota.value if self.nota.value else "Nenhuma"
        embed_log.add_field(name="Nota Privada da Staff", value=nota_txt, inline=False)
        embed_dm = discord.Embed(title=f"{titulo} - Candidatura {decisao_txt}", description=f"Voce enviou uma candidatura para **{titulo}**\n\n{self.respostas}", color=cor)
        embed_dm.add_field(name="Decisao", value=decisao_txt, inline=True)
        embed_dm.add_field(name="Decidido Por", value=interaction.user.mention, inline=True)
        embed_dm.add_field(name="Motivo", value=self.motivo.value, inline=False)
        canal_log = guild.get_channel(form["canal_log_id"]) if form else interaction.channel
        if canal_log:
            await canal_log.send(embed=embed_log)
        try:
            await candidato.send(embed=embed_dm)
        except:
            pass
        try:
            await interaction.message.edit(view=None)
        except:
            pass
        await interaction.response.send_message(f"✅ Decisao registrada como **{decisao_txt}**", ephemeral=True)

class ViewDecisao(discord.ui.View):
    def __init__(self, painel_id, candidato_id, respostas):
        super().__init__(timeout=None)
        self.painel_id = painel_id
        self.candidato_id = candidato_id
        self.respostas = respostas
    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, custom_id="aprovar_btn", emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not tem_cargo_staff(interaction.user):
            return await interaction.response.send_message("❌ So Dono / Vice Dono / Gerente pode decidir.", ephemeral=True)
        modal = ModalDecisao(True, self.painel_id, self.candidato_id, self.respostas)
        await interaction.response.send_modal(modal)
    @discord.ui.button(label="Reprovar", style=discord.ButtonStyle.danger, custom_id="reprovar_btn", emoji="❌")
    async def reprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not tem_cargo_staff(interaction.user):
            return await interaction.response.send_message("❌ So Dono / Vice Dono / Gerente pode decidir.", ephemeral=True)
        modal = ModalDecisao(False, self.painel_id, self.candidato_id, self.respostas)
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comandos")
    except Exception as e:
        print(e)

@bot.tree.command(name="criarpainelformulario", description="Criar um novo painel de formulario")
@app_commands.describe(canal_publicar="Onde o painel vai aparecer", canal_log="Onde cai as candidaturas", cargo_aprovado="Cargo ao aprovar", cargo_reprovado="Cargo ao reprovar")
async def criarpainelformulario(interaction: discord.Interaction, canal_publicar: discord.TextChannel, canal_log: discord.TextChannel, cargo_aprovado: discord.Role = None, cargo_reprovado: discord.Role = None):
    if not tem_cargo_staff(interaction.user):
        return await interaction.response.send_message("❌ So Dono / Vice Dono / Gerente pode criar painel.", ephemeral=True)
    modal = ModalCriarPainel(canal_publicar, canal_log, cargo_aprovado, cargo_reprovado)
    await interaction.response.send_modal(modal)

@bot.tree.command(name="adicionar-pergunta", description="Adicionar pergunta em um painel")
@app_commands.describe(id_painel="ID da mensagem do painel", pergunta="A pergunta")
async def add_pergunta(interaction: discord.Interaction, id_painel: str, pergunta: str):
    if not tem_cargo_staff(interaction.user):
        return await interaction.response.send_message("❌ Sem permissao.", ephemeral=True)
    form = forms.get(id_painel)
    if not form:
        return await interaction.response.send_message("❌ Painel nao encontrado. Verifique o ID.", ephemeral=True)
    form["perguntas"].append(pergunta)
    total = len(form["perguntas"])
    await interaction.response.send_message(f"✅ Pergunta adicionada! Total: {total}\nPergunta: {pergunta}", ephemeral=True)

bot.run(TOKEN)
