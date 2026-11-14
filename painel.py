import discord
from discord import app_commands
from discord.ext import commands
import json, os

DATA_FILE = "data_paineis.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"paineis": {}, "config": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_config(guild_id):
    data = load_data()
    return data["config"].get(str(guild_id), {"cargos_membros": [], "log_formulario": None, "cargos_acesso_bot": []})

def save_config(guild_id, cfg):
    data = load_data()
    data["config"][str(guild_id)] = cfg
    save_data(data)

def tem_acesso_bot(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        return True
    cfg = get_config(interaction.guild.id)
    cargos_permitidos = cfg.get("cargos_acesso_bot", [])
    if not cargos_permitidos:
        return False
    user_role_ids = [r.id for r in interaction.user.roles]
    return any(rid in user_role_ids for rid in cargos_permitidos)

class GerenciarPaineisView(discord.ui.View):
    def __init__(self, guild_id, pagina=0):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.pagina = pagina
        self.por_pagina = 5

    def get_embed(self):
        data = load_data()
        paineis = list(data["paineis"].get(str(self.guild_id), {}).values())
        total_pag = max(1, (len(paineis) + self.por_pagina - 1) // self.por_pagina)
        self.pagina = max(0,