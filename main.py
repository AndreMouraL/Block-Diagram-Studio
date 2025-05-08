#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
import time
import os
import sys
from PIL import Image, ImageTk

class LoadingScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Block Diagram Studio - Carregando")
        self.root.geometry("400x300")
        
        # Tenta carregar o ícone
        try:
            self.root.iconbitmap(r'ico\circ.ico')
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")

        self.root.resizable(False, False)
        
        # Centraliza a janela
        self._center_window()
        
        # Configura o fundo claro
        self.root.configure(bg='#F0FFF0')
        
        # Carrega e exibe o logo
        self._load_logo()
        
        # Configura o estilo da barra de progresso
        self._setup_progressbar_style()
        
        # Barra de progresso
        self.progress = ttk.Progressbar(
            self.root, 
            orient=tk.HORIZONTAL, 
            length=300, 
            mode='determinate',
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=20)
        
        # Label de status
        self.status_label = tk.Label(
            self.root, 
            text="Inicializando...", 
            bg='#F0FFF0', 
            fg='#0A2667',
            font=('Arial', 10)
        )
        self.status_label.pack(pady=10)
        
        # Inicia a animação de carregamento
        self._start_loading()

    def _center_window(self):
        """Centraliza a janela na tela"""
        window_width = self.root.winfo_reqwidth()
        window_height = self.root.winfo_reqheight()
        position_right = int(self.root.winfo_screenwidth()/2 - window_width/2)
        position_down = int(self.root.winfo_screenheight()/2 - window_height/2)
        self.root.geometry(f"+{position_right}+{position_down}")

    def _load_logo(self):
        """Carrega e exibe o logo da aplicação"""
        try:
            # Tenta carregar o logo (substitua pelo caminho correto)
            logo_path = self._get_resource_path('img/blk.png')
            logo_img = Image.open(logo_path)
            logo_img = logo_img.resize((150, 150), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(logo_img)
            
            logo_label = tk.Label(
                self.root, 
                image=self.logo, 
                bg='#F0FFF0'
            )
            logo_label.pack(pady=20)
            
        except Exception as e:
            # Fallback se o logo não for encontrado
            print(f"Erro ao carregar logo: {e}")
            title_label = tk.Label(
                self.root, 
                text="Block Diagram Studio", 
                bg='#F0FFF0', 
                fg='#006400',
                font=('Arial', 16, 'bold')
            )
            title_label.pack(pady=40)

    def _setup_progressbar_style(self):
        """Configura o estilo personalizado para a barra de progresso"""
        style = ttk.Style()
        style.theme_use('clam')  # Tema que permite mais customização
        
        # Estilo personalizado para a barra de progresso
        style.configure("Custom.Horizontal.TProgressbar",
                       thickness=10,
                       troughcolor='#E0E0E0',
                       background='#0A2667',
                       bordercolor='#0A2667',
                       lightcolor='#0A2667',
                       darkcolor='#0A2667',
                       troughrelief='flat',
                       relief='flat')

    def _get_resource_path(self, relative_path):
        """Obtém o caminho absoluto para recursos incluídos no executável"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
            
        return os.path.join(base_path, relative_path)

    def _start_loading(self):
        """Inicia a animação de carregamento"""
        self.progress["value"] = 0
        self.root.after(100, self._update_progress)

    def _update_progress(self):
        """Atualiza a barra de progresso"""
        current_value = self.progress["value"]
        
        if current_value < 100:
            # Atualiza o progresso
            increment = 5 if current_value < 70 else 2
            new_value = min(current_value + increment, 100)
            self.progress["value"] = new_value
            
            # Atualiza a mensagem de status
            if new_value < 30:
                self.status_label.config(text="Carregando componentes...")
            elif new_value < 60:
                self.status_label.config(text="Preparando interface...")
            elif new_value < 90:
                self.status_label.config(text="Inicializando bibliotecas...")
            else:
                self.status_label.config(text="Quase pronto...")
            
            # Agenda a próxima atualização
            self.root.after(100, self._update_progress)
        else:
            # Quando o carregamento terminar, fecha a tela e abre a aplicação principal
            self.root.after(500, self._launch_main_app)

    def _launch_main_app(self):
        """Fecha a tela de carregamento e abre a aplicação principal"""
        self.root.destroy()
        
        # Importa e inicia a aplicação principal
        from block import BlockDiagramAcadApp
        
        root = tk.Tk()
        app = BlockDiagramAcadApp(root)
        root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    loading_screen = LoadingScreen(root)
    root.mainloop()