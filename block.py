#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import control as ctl
import sympy as sp
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.utils import ImageReader
import matplotlib.patheffects as pe
import copy

# Símbolo de Laplace para Sympy
s_sym = sp.symbols('s')

def configure_style():
    style = ttk.Style()
    style.theme_use('clam')  # Usando o tema 'clam' que é mais customizável
    
    # Cores base - fundo branco e texto azul escuro
    style.configure('.', background='white', foreground='#0A2667')  
    style.configure('TFrame', background='white')
    style.configure('TLabel', background='white', foreground='#0A2667')
    style.configure('TButton', background='#0A2667', foreground='white', 
                   bordercolor='#0A2667', lightcolor='#0A2667', darkcolor='#0A2667')
    style.configure('TEntry', fieldbackground='white', foreground='#0A2667')
    style.configure('TCombobox', fieldbackground='white', foreground='#0A2667')
    style.configure('TNotebook', background='white')
    style.configure('TNotebook.Tab', background='#D6E4FF', foreground='#0A2667',
                   padding=[10, 5])
    style.map('TNotebook.Tab', background=[('selected', '#0A2667')], foreground=[('selected', 'white')])
    style.configure('TListbox', background='white', foreground='#0A2667')
    style.configure('Vertical.TScrollbar', background='#D6E4FF')
    style.configure('Horizontal.TScrollbar', background='#D6E4FF')
    style.configure('TLabelframe', background='white', foreground='#0A2667')
    style.configure('TLabelframe.Label', background='white', foreground='#0A2667')

class BlockDiagram:
    """Armazena os blocos e reduz o diagrama."""
    def __init__(self):
        self.edges = []
        self.feedback_signs = {}  # Armazena os sinais de feedback

    def add_block(self, u: str, v: str, tf: ctl.TransferFunction, sign='+'):
        # Verifica se o bloco já existe
        for edge in self.edges:
            if edge['u'] == u and edge['v'] == v:
                raise ValueError(f"Bloco {u}→{v} já existe!")
        
        self.edges.append({'u': u, 'v': v, 'tf': tf})
        if u != 'input' and v != 'output':  # Assume que é um bloco de feedback
            self.feedback_signs[(u, v)] = sign

    def _find_series_blocks(self):
        """Encontra blocos em série que podem ser reduzidos."""
        # Cria um mapeamento de saídas para blocos
        output_map = {e['v']: e for e in self.edges}
        
        for e in list(self.edges):  # Usamos list() para criar uma cópia
            # Se houver um bloco que começa onde este termina
            if e['v'] in output_map and e['v'] != 'output' and e['u'] != 'output':
                e2 = output_map[e['v']]
                if e2 in self.edges:  # Verifica se ainda está na lista
                    return e, e2
        return None, None

    def _find_parallel_blocks(self):
        """Encontra blocos em paralelo que podem ser reduzidos."""
        edges_copy = list(self.edges)  # Trabalha com uma cópia
        for i in range(len(edges_copy)):
            for j in range(i+1, len(edges_copy)):
                e1 = edges_copy[i]
                e2 = edges_copy[j]
                if e1['u'] == e2['u'] and e1['v'] == e2['v']:
                    # Verifica se ambos ainda estão na lista principal
                    if e1 in self.edges and e2 in self.edges:
                        return e1, e2
        return None, None

    def _find_feedback_blocks(self):
        """Encontra blocos em realimentação que podem ser reduzidos."""
        edges_copy = list(self.edges)  # Trabalha com uma cópia
        for i in range(len(edges_copy)):
            for j in range(len(edges_copy)):
                if i == j:
                    continue
                e1 = edges_copy[i]
                e2 = edges_copy[j]
                if e1['u'] == e2['v'] and e1['v'] == e2['u']:
                    # Verifica se ambos ainda estão na lista principal
                    if e1 in self.edges and e2 in self.edges:
                        return e1, e2
        return None, None

    def reduce(self) -> ctl.TransferFunction:
        """Reduz o diagrama de blocos até obter uma única função de transferência."""
        edges = copy.deepcopy(self.edges)
        feedback_signs = copy.deepcopy(self.feedback_signs)
        
        changed = True
        while changed and len(edges) > 1:
            changed = False
            
            # Tenta reduzir série primeiro
            e1, e2 = self._find_series_blocks()
            if e1 and e2 and e1 in edges and e2 in edges:
                new_tf = ctl.series(e1['tf'], e2['tf'])
                edges.remove(e1)
                edges.remove(e2)
                edges.append({'u': e1['u'], 'v': e2['v'], 'tf': new_tf})
                changed = True
                continue
                
            # Tenta reduzir paralelo
            e1, e2 = self._find_parallel_blocks()
            if e1 and e2 and e1 in edges and e2 in edges:
                new_tf = ctl.parallel(e1['tf'], e2['tf'])
                edges.remove(e1)
                edges.remove(e2)
                edges.append({'u': e1['u'], 'v': e1['v'], 'tf': new_tf})
                changed = True
                continue
                
            # Tenta reduzir realimentação
            fwd, fb = self._find_feedback_blocks()
            if fwd and fb and fwd in edges and fb in edges:
                sign = feedback_signs.get((fb['u'], fb['v']), '-')
                new_tf = ctl.feedback(fwd['tf'], fb['tf'], sign=sign)
                edges.remove(fwd)
                edges.remove(fb)
                edges.append({'u': fwd['u'], 'v': fwd['v'], 'tf': new_tf})
                changed = True
                continue

        # Verifica se sobrou apenas um bloco input->output
        remaining = [e for e in edges if e['u'] == 'input' and e['v'] == 'output']
        if len(remaining) == 1:
            return remaining[0]['tf']

        # Se não conseguiu reduzir, tenta combinar os blocos de outra forma
        if len(edges) > 1:
            # Tenta combinar todos os blocos em paralelo
            try:
                parallel_tf = edges[0]['tf']
                for e in edges[1:]:
                    parallel_tf = ctl.parallel(parallel_tf, e['tf'])
                return parallel_tf
            except:
                pass

        raise ValueError(f"Não foi possível reduzir ({len(edges)} blocos). Diagrama muito complexo ou mal formado.")

class BlockDiagramAcadApp:
    """Interface principal com abas: Entrada, Diagrama e Análise."""
    def __init__(self, root):
        self.root = root
        root.title("Block Diagram Studio – Acadêmico")
        root.geometry("1000x750")
        configure_style()
        root.configure(bg='white')
        
        try:
            self.root.iconbitmap(r'ico\circ.ico')
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")

        self.bd = BlockDiagram()
        self.current_tf = None  # Armazena a função de transferência atual
        self._build_ui()

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True)

        tab1 = ttk.Frame(nb); nb.add(tab1, text="Entrada")
        self._build_tab_input(tab1)

        tab2 = ttk.Frame(nb); nb.add(tab2, text="Diagrama")
        self._build_tab_diagram(tab2)

        tab3 = ttk.Frame(nb); nb.add(tab3, text="Análise")
        self._build_tab_analysis(tab3)

    # Aba "Entrada"
    def _build_tab_input(self, frame):
        pad = dict(padx=5, pady=5)

        # Frame principal dividido em esquerda (formulário) e direita (imagens)
        main_frame = ttk.Frame(frame)
        main_frame.pack(fill=tk.BOTH, expand=True)
        # Frame para o formulário (lado esquerdo)
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        fmt = ttk.LabelFrame(frame, text="Formato de TF")
        fmt.pack(fill=tk.X, **pad)

        self.var_fmt = tk.StringVar(master=self.root, value='coef')
        ttk.Radiobutton(fmt, text="Coeficientes",
                        variable=self.var_fmt, value='coef',
                        command=self._toggle_format).pack(side=tk.LEFT, **pad)
        ttk.Radiobutton(fmt, text="Polinomial",
                        variable=self.var_fmt, value='poly',
                        command=self._toggle_format).pack(side=tk.LEFT, **pad)

        ef = ttk.Frame(frame); ef.pack(fill=tk.X, **pad)
        ttk.Label(ef, text="Origem:").grid(row=0, column=0, **pad)
        self.e_u = ttk.Entry(ef, width=12); self.e_u.grid(row=0, column=1, **pad)
        ttk.Label(ef, text="Destino:").grid(row=0, column=2, **pad)
        self.e_v = ttk.Entry(ef, width=12); self.e_v.grid(row=0, column=3, **pad)

        # Adicionando opção de sinal para feedback
        ttk.Label(ef, text="Sinal:").grid(row=0, column=4, **pad)
        self.e_sign = ttk.Combobox(ef, values=['+', '-'], width=3)
        self.e_sign.grid(row=0, column=5, **pad)
        self.e_sign.set('-')  # Padrão para feedback negativo

        ttk.Label(ef, text="Num coef.:").grid(row=1, column=0, **pad)
        self.e_num = ttk.Entry(ef, width=40); self.e_num.grid(row=1, column=1, columnspan=5, **pad)
        ttk.Label(ef, text="Den coef.:").grid(row=2, column=0, **pad)
        self.e_den = ttk.Entry(ef, width=40); self.e_den.grid(row=2, column=1, columnspan=5, **pad)

        ttk.Label(ef, text="Num poly:").grid(row=3, column=0, **pad)
        self.e_num_poly = ttk.Entry(ef, width=40); self.e_num_poly.grid(row=3, column=1, columnspan=5, **pad)
        ttk.Label(ef, text="Den poly:").grid(row=4, column=0, **pad)
        self.e_den_poly = ttk.Entry(ef, width=40); self.e_den_poly.grid(row=4, column=1, columnspan=5, **pad)

        pv = ttk.LabelFrame(frame, text="Pré-visualização G(s)")
        pv.pack(fill=tk.BOTH, **pad)
        self.fig_prev = plt.Figure(figsize=(4,1), facecolor='white')
        self.ax_prev = self.fig_prev.add_subplot(111); self.ax_prev.axis('off')
        self.ax_prev.set_facecolor('white')
        self.canvas_prev = FigureCanvasTkAgg(self.fig_prev, master=pv)
        self.canvas_prev.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        for w in (self.e_num, self.e_den, self.e_num_poly, self.e_den_poly):
            w.bind("<KeyRelease>", lambda e: self._update_preview())

        ttk.Button(frame, text="➕ Adicionar Bloco", command=self._on_add_block).pack(**pad)

        lf = ttk.LabelFrame(frame, text="Blocos Cadastrados")
        lf.pack(fill=tk.BOTH, expand=True, **pad)
        
        # Frame para os botões de ação
        btn_frame = ttk.Frame(lf)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Botão para deletar bloco selecionado
        ttk.Button(btn_frame, text="🗑️ Deletar Selecionado", 
                  command=self._delete_selected_block).pack(side=tk.LEFT, padx=5)
        
        # Botão para limpar todos os blocos
        ttk.Button(btn_frame, text="🧹 Limpar Todos", 
                  command=self._clear_all_blocks).pack(side=tk.LEFT, padx=5)
        
        self.lst = tk.Listbox(lf, bg='white', fg='#0A2667')
        self.lst.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        sb = ttk.Scrollbar(lf, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        sb.config(command=self.lst.yview)
        self.lst.config(yscrollcommand=sb.set)
        
        # Adiciona bind para deletar com tecla Delete
        self.lst.bind('<Delete>', lambda e: self._delete_selected_block())

        # Frame para as imagens (lado direito)
        img_frame = ttk.Frame(main_frame, width=300)
        img_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
 
        # Carrega e exibe as imagens
        try:
            from PIL import Image, ImageTk
        
            # Primeira imagem (substitua pelo caminho da sua primeira imagem)
            img1_path = r'img/blk.png'#
            img1 = Image.open(img1_path)
            img1 = img1.resize((40, 35), Image.LANCZOS)  # Redimensiona mantendo proporção
            img1_tk = ImageTk.PhotoImage(img1)
        
            # Cria um Label com borda para a imagem
            img1_label = ttk.Label(img_frame, image=img1_tk, 
                                 borderwidth=2, relief="solid")
            img1_label.image = img1_tk  # Mantém uma referência
            img1_label.pack(pady=(0, 10))
        
        except Exception as e:
            print(f"Erro ao carregar imagens: {e}")
            ttk.Label(img_frame, text="Imagens não encontradas").pack()

    def _delete_selected_block(self):
        """Remove o bloco selecionado da lista."""
        selection = self.lst.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Nenhum bloco selecionado!")
            return
            
        index = selection[0]
        block_info = self.lst.get(index)
        
        # Extrai origem e destino do bloco (formato: "origem→destino (sinal) : $TF$")
        parts = block_info.split(" : ")[0].split("→")
        if len(parts) != 2:
            messagebox.showerror("Erro", "Formato de bloco inválido!")
            return
            
        u = parts[0].strip()
        v_part = parts[1].split(" (")[0].strip()
        
        # Remove o bloco da lista visual
        self.lst.delete(index)
        
        # Remove o bloco da estrutura de dados
        for edge in list(self.bd.edges):
            if edge['u'] == u and edge['v'] == v_part:
                self.bd.edges.remove(edge)
                # Remove também do dicionário de sinais se existir
                if (u, v_part) in self.bd.feedback_signs:
                    del self.bd.feedback_signs[(u, v_part)]
                break
        
        # Atualiza o diagrama
        self._draw_graph()
        messagebox.showinfo("Sucesso", "Bloco removido com sucesso!")

    def _clear_all_blocks(self):
        """Remove todos os blocos cadastrados."""
        if not self.bd.edges:
            messagebox.showinfo("Informação", "Não há blocos para remover!")
            return
            
        if messagebox.askyesno("Confirmar", "Deseja realmente remover TODOS os blocos?"):
            self.bd.edges.clear()
            self.bd.feedback_signs.clear()
            self.lst.delete(0, tk.END)
            self._draw_graph()
            messagebox.showinfo("Sucesso", "Todos os blocos foram removidos!")

    def _toggle_format(self):
        coef = (self.var_fmt.get() == 'coef')
        for w, show in ((self.e_num, coef), (self.e_den, coef),
                        (self.e_num_poly, not coef), (self.e_den_poly, not coef)):
            (w.grid() if show else w.grid_remove())

    def _update_preview(self):
        try:
            if self.var_fmt.get() == 'coef':
                num = [float(c) for c in self.e_num.get().split()]
                den = [float(c) for c in self.e_den.get().split()]
            else:
                pn = sp.parse_expr(self.e_num_poly.get().replace('^','**'), {'s': s_sym})
                pd = sp.parse_expr(self.e_den_poly.get().replace('^','**'), {'s': s_sym})
                num = [float(c) for c in sp.Poly(pn, s_sym).all_coeffs()]
                den = [float(c) for c in sp.Poly(pd, s_sym).all_coeffs()]
            ne = sum(c*s_sym**i for i, c in enumerate(reversed(num)))
            de = sum(c*s_sym**i for i, c in enumerate(reversed(den)))
            tex = sp.latex(sp.simplify(ne/de))
        except:
            tex = r"\text{Inválido}"
        self.ax_prev.clear()
        self.ax_prev.text(0.1, 0.5, f"$G(s)={tex}$", size=14, color='#0A2667')
        self.ax_prev.axis('off')
        self.ax_prev.set_facecolor('white')
        self.canvas_prev.draw()

    def _on_add_block(self):
        u, v = self.e_u.get().strip(), self.e_v.get().strip()
        sign = self.e_sign.get().strip()
        if not u or not v:
            return messagebox.showwarning("Aviso", "Origem e Destino obrigatórios.")
        try:
            if self.var_fmt.get() == 'coef':
                num = [float(c) for c in self.e_num.get().split()]
                den = [float(c) for c in self.e_den.get().split()]
            else:
                pn = sp.parse_expr(self.e_num_poly.get().replace('^','**'), {'s': s_sym})
                pd = sp.parse_expr(self.e_den_poly.get().replace('^','**'), {'s': s_sym})
                num = [float(c) for c in sp.Poly(pn, s_sym).all_coeffs()]
                den = [float(c) for c in sp.Poly(pd, s_sym).all_coeffs()]
        except Exception as e:
            return messagebox.showerror("Erro", str(e))

        try:
            tf = ctl.TransferFunction(num, den)
            self.bd.add_block(u, v, tf, sign)
        except ValueError as e:
            return messagebox.showerror("Erro", str(e))

        ne = sum(c*s_sym**i for i, c in enumerate(reversed(num)))
        de = sum(c*s_sym**i for i, c in enumerate(reversed(den)))
        expr = sp.latex(sp.simplify(ne/de))
        self.lst.insert(tk.END, f"{u}→{v} ({sign}) : ${expr}$")

        self._draw_graph()
        self._update_preview()

        for w in (self.e_u, self.e_v, self.e_num, self.e_den,
                  self.e_num_poly, self.e_den_poly):
            w.delete(0, tk.END)

    # Aba "Diagrama"
    def _build_tab_diagram(self, frame):
        self.fig_graph = plt.Figure(figsize=(5,4), facecolor='white')
        self.ax_graph = self.fig_graph.add_subplot(111)
        self.ax_graph.axis('off')
        self.ax_graph.set_facecolor('white')
        self.canvas_graph = FigureCanvasTkAgg(self.fig_graph, master=frame)
        self.canvas_graph.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _draw_graph(self):
        ax = self.ax_graph
        ax.clear()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_facecolor('white')

        if not self.bd.edges:
            self.canvas_graph.draw()
            return

        # 1) Extrai forward e feedback
        forward, feedback = [], []
        used = set()
        current = 'input'
        
        # Tenta encontrar o caminho direto
        while current != 'output' and current is not None:
            next_edge = None
            for e in self.bd.edges:
                if e['u'] == current and (e['u'], e['v']) not in used:
                    next_edge = e
                    break
            
            if next_edge is None:
                break
                
            forward.append(next_edge)
            used.add((next_edge['u'], next_edge['v']))
            current = next_edge['v']

        # O restante são feedbacks
        for e in self.bd.edges:
            if (e['u'], e['v']) not in used:
                feedback.append(e)

        N = len(forward)
        if N == 0:
            self.canvas_graph.draw()
            return

        # 2) Posições
        x0, xN = 0.1, 0.9
        xs = [x0 + i*(xN-x0)/(N+1) for i in range(N+2)]
        y0, yfb = 0.5, 0.25
        sum_pos    = (xs[0], y0)
        block_pos  = [(xs[i+1], y0) for i in range(N)]
        branch_pos = (xs[-1], y0)
        fb_elbow_v = (branch_pos[0], yfb)
        fb_elbow_h = (sum_pos[0], yfb)

        # 3) Estilos de seta
        arrow_head = dict(
            arrowstyle='-|>',
            mutation_scale=15,
            linewidth=2,
            color='#0A2667',  # Azul escuro
            shrinkA=15,
            shrinkB=15,
            connectionstyle='arc3,rad=0',
            zorder=2
        )
        arrow_line = dict(
            arrowstyle='-',
            linewidth=2,
            color='#0A2667',  # Azul escuro
            shrinkA=15,
            shrinkB=15,
            connectionstyle='arc3,rad=0',
            zorder=2
        )

        # 4) Somador e R(s)
        if feedback:
            circ = patches.Circle(sum_pos, 0.05, linewidth=2,
                                edgecolor='#0A2667', facecolor='white', zorder=3)
            circ.set_path_effects([pe.Stroke(linewidth=3, foreground='black', alpha=0.3),
                                pe.Normal()])
            ax.add_patch(circ)
            
            # Determina o sinal do feedback
            fb_sign = '-'
            for e in feedback:
                if (e['u'], e['v']) in self.bd.feedback_signs:
                    fb_sign = self.bd.feedback_signs[(e['u'], e['v'])]
                    break
                    
            ax.text(sum_pos[0]+0.03, sum_pos[1]+0.03, '+',
                    ha='center', va='center', fontsize=16, color='#0A2667')
            ax.text(sum_pos[0]-0.03, sum_pos[1]-0.03, fb_sign,
                    ha='center', va='center', fontsize=16, color='#0A2667')
                    
            ax.annotate("", xy=sum_pos, xytext=(0, y0), arrowprops=arrow_head)
            ax.text(0, y0, "$R(s)$", ha='left', va='center', fontsize=12, color='#0A2667')
        else:
            ax.annotate("", xy=block_pos[0], xytext=(0, y0), arrowprops=arrow_head)
            ax.text(0, y0, "$R(s)$", ha='left', va='center', fontsize=12, color='#0A2667')

        # 5) Forward path
        for i, e in enumerate(forward):
            x, y = block_pos[i]
            rect = patches.FancyBboxPatch((x-0.08, y-0.05), 0.16, 0.10,
                                        boxstyle="round,pad=0.03", linewidth=2,
                                        edgecolor='#0A2667', facecolor='#3A5FCD', zorder=3)  # Azul médio
            rect.set_path_effects([pe.Stroke(linewidth=4, foreground='black', alpha=0.2),
                                pe.Normal()])
            ax.add_patch(rect)

            num, den = e['tf'].num[0][0], e['tf'].den[0][0]
            ne = sum(c*s_sym**k for k, c in enumerate(reversed(num)))
            de = sum(c*s_sym**k for k, c in enumerate(reversed(den)))
            gs = sp.latex(sp.simplify(ne/de))
            ax.text(x, y, f"${gs}$", ha='center', va='center',
                    fontsize=12, color='white',
                    path_effects=[pe.Stroke(linewidth=1.5, foreground='black'),
                                pe.Normal()])

            src = sum_pos if i == 0 else block_pos[i-1]
            ax.annotate("", xy=(x-0.08, y), xytext=(src[0]+0.08, y),
                        arrowprops=arrow_head)

        # 6) Ramificação e C(s)
        ax.annotate("", xy=branch_pos, xytext=(block_pos[-1][0]+0.08, y0),
                    arrowprops=arrow_head)
        dot = patches.Circle(branch_pos, 0.02, facecolor='#0A2667', edgecolor='#0A2667', zorder=3)
        ax.add_patch(dot)
        ax.annotate("", xy=(1.0, y0), xytext=(branch_pos[0]+0.02, y0),
                    arrowprops=arrow_head)
        ax.text(1.0, y0, "$C(s)$", ha='left', va='center', fontsize=12, color='#0A2667')

        # 7) Feedback em "L"
        for e in feedback:
            ax.annotate("", xy=fb_elbow_v, xytext=branch_pos, arrowprops=arrow_line)
            ax.annotate("", xy=fb_elbow_h, xytext=fb_elbow_v, arrowprops=arrow_line)
            ax.annotate("", xy=sum_pos, xytext=fb_elbow_h, arrowprops=arrow_head)

            # bloco de feedback
            h_x, h_y = (sum_pos[0] + branch_pos[0]) / 2, yfb
            rect_fb = patches.FancyBboxPatch((h_x-0.05, h_y-0.025), 0.10, 0.05,
                                            boxstyle="round,pad=0.02", linewidth=2,
                                            edgecolor='#0A2667', facecolor='#B0C4DE', zorder=3)  # Azul claro
            rect_fb.set_path_effects([pe.Stroke(linewidth=2, foreground='black', alpha=0.3),
                                    pe.Normal()])
            ax.add_patch(rect_fb)

            num, den = e['tf'].num[0][0], e['tf'].den[0][0]
            ne = sum(c*s_sym**k for k, c in enumerate(reversed(num)))
            de = sum(c*s_sym**k for k, c in enumerate(reversed(den)))
            hs = sp.latex(sp.simplify(ne/de))
            ax.text(h_x, h_y, f"${hs}$", ha='center', va='center', fontsize=10,
                    color='#0A2667',
                    path_effects=[pe.Stroke(linewidth=1, foreground='white'),
                                pe.Normal()])

        self.canvas_graph.draw()

    # Aba "Análise"
    def _build_tab_analysis(self, frame):
        pad = dict(padx=5, pady=5)
        
        # Frame superior para botões de análise
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, **pad)
        
        # Frame para botões de cálculo de blocos
        calc_frame = ttk.LabelFrame(top_frame, text="Cálculo de Blocos")
        calc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, **pad)
        
        ttk.Button(calc_frame, text="Blocos em Série", 
                  command=self._calc_series).pack(side=tk.LEFT, **pad)
        ttk.Button(calc_frame, text="Blocos em Paralelo", 
                  command=self._calc_parallel).pack(side=tk.LEFT, **pad)
        ttk.Button(calc_frame, text="Realimentação (G e H)", 
                  command=self._calc_feedback).pack(side=tk.LEFT, **pad)
        
        # Frame para botões de análise do sistema
        analysis_frame = ttk.LabelFrame(top_frame, text="Análise do Sistema")
        analysis_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, **pad)
        
        ttk.Button(analysis_frame, text="Calcular G(s)", 
                  command=self._on_calc).pack(side=tk.LEFT, **pad)
        ttk.Button(analysis_frame, text="Bode", 
                  command=self._plot_bode).pack(side=tk.LEFT, **pad)
        ttk.Button(analysis_frame, text="Degrau", 
                  command=self._plot_step).pack(side=tk.LEFT, **pad)
        ttk.Button(analysis_frame, text="Exportar PDF", 
                  command=self._export_pdf).pack(side=tk.LEFT, **pad)

        # Frame para entrada de funções de transferência
        input_frame = ttk.LabelFrame(frame, text="Entrada para Cálculos")
        input_frame.pack(fill=tk.X, **pad)
        
        # Entrada para G(s)
        ttk.Label(input_frame, text="G(s):").grid(row=0, column=0, sticky=tk.W, **pad)
        self.g_num_entry = ttk.Entry(input_frame, width=30)
        self.g_num_entry.grid(row=0, column=1, **pad)
        ttk.Label(input_frame, text="/").grid(row=0, column=2, **pad)
        self.g_den_entry = ttk.Entry(input_frame, width=30)
        self.g_den_entry.grid(row=0, column=3, **pad)
        
        # Entrada para H(s)
        ttk.Label(input_frame, text="H(s):").grid(row=1, column=0, sticky=tk.W, **pad)
        self.h_num_entry = ttk.Entry(input_frame, width=30)
        self.h_num_entry.grid(row=1, column=1, **pad)
        ttk.Label(input_frame, text="/").grid(row=1, column=2, **pad)
        self.h_den_entry = ttk.Entry(input_frame, width=30)
        self.h_den_entry.grid(row=1, column=3, **pad)
        
        # Resultado dos cálculos
        self.fig_tf = plt.Figure(figsize=(5,1.5), facecolor='white')
        self.ax_tf = self.fig_tf.add_subplot(111); self.ax_tf.axis('off')
        self.ax_tf.set_facecolor('white')
        self.canvas_tf = FigureCanvasTkAgg(self.fig_tf, master=frame)
        self.canvas_tf.get_tk_widget().pack(fill=tk.X, **pad)

        # Gráficos de análise
        self.fig_plot = plt.Figure(figsize=(5,3), facecolor='white')
        self.ax_plot = self.fig_plot.add_subplot(111)
        self.ax_plot.set_facecolor('white')
        for spine in self.ax_plot.spines.values():
            spine.set_color('#0A2667')
        self.ax_plot.tick_params(axis='x', colors='#0A2667')
        self.ax_plot.tick_params(axis='y', colors='#0A2667')
        self.ax_plot.yaxis.label.set_color('#0A2667')
        self.ax_plot.xaxis.label.set_color('#0A2667')
        self.ax_plot.title.set_color('#0A2667')
        self.canvas_plot = FigureCanvasTkAgg(self.fig_plot, master=frame)
        self.canvas_plot.get_tk_widget().pack(fill=tk.BOTH, expand=True, **pad)

    def _get_tf_from_entries(self, num_entry, den_entry):
        """Obtém uma função de transferência a partir das entradas de numerador e denominador."""
        try:
            num_str = num_entry.get().strip()
            den_str = den_entry.get().strip()
            
            if not num_str or not den_str:
                raise ValueError("Numerador e denominador são obrigatórios!")
                
            # Tenta interpretar como coeficientes
            try:
                num = [float(c) for c in num_str.split()]
                den = [float(c) for c in den_str.split()]
                return ctl.TransferFunction(num, den)
            except:
                # Se falhar, tenta interpretar como expressão polinomial
                num_poly = sp.parse_expr(num_str.replace('^','**'), {'s': s_sym})
                den_poly = sp.parse_expr(den_str.replace('^','**'), {'s': s_sym})
                num = [float(c) for c in sp.Poly(num_poly, s_sym).all_coeffs()]
                den = [float(c) for c in sp.Poly(den_poly, s_sym).all_coeffs()]
                return ctl.TransferFunction(num, den)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao processar função de transferência:\n{str(e)}")
            return None

    def _calc_series(self):
        """Calcula a conexão em série de G(s) e H(s)."""
        g_tf = self._get_tf_from_entries(self.g_num_entry, self.g_den_entry)
        h_tf = self._get_tf_from_entries(self.h_num_entry, self.h_den_entry)
        
        if g_tf is None or h_tf is None:
            return
            
        try:
            result_tf = ctl.series(g_tf, h_tf)
            self._show_tf_result(result_tf, "Conexão em Série G(s)H(s)")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao calcular série:\n{str(e)}")

    def _calc_parallel(self):
        """Calcula a conexão em paralelo de G(s) e H(s)."""
        g_tf = self._get_tf_from_entries(self.g_num_entry, self.g_den_entry)
        h_tf = self._get_tf_from_entries(self.h_num_entry, self.h_den_entry)
        
        if g_tf is None or h_tf is None:
            return
            
        try:
            result_tf = ctl.parallel(g_tf, h_tf)
            self._show_tf_result(result_tf, "Conexão em Paralelo G(s)+H(s)")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao calcular paralelo:\n{str(e)}")

    def _calc_feedback(self):
        """Calcula a realimentação de G(s) e H(s)."""
        g_tf = self._get_tf_from_entries(self.g_num_entry, self.g_den_entry)
        h_tf = self._get_tf_from_entries(self.h_num_entry, self.h_den_entry)
        
        if g_tf is None or h_tf is None:
            return
            
        try:
            result_tf = ctl.feedback(g_tf, h_tf)
            self._show_tf_result(result_tf, "Realimentação G(s)/(1±G(s)H(s))")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao calcular realimentação:\n{str(e)}")

    def _show_tf_result(self, tf, title):
        """Exibe o resultado de uma função de transferência."""
        num, den = tf.num[0][0], tf.den[0][0]
        ne = sum(c*s_sym**i for i, c in enumerate(reversed(num)))
        de = sum(c*s_sym**i for i, c in enumerate(reversed(den)))
        tex = sp.latex(sp.simplify(ne/de))

        self.ax_tf.clear()
        self.ax_tf.text(0.1, 0.7, title, size=12, color='#0A2667')
        self.ax_tf.text(0.1, 0.3, f"$Resultado = {tex}$", size=14, color='#0A2667')
        self.ax_tf.axis('off')
        self.ax_tf.set_facecolor('white')
        self.canvas_tf.draw()

    def _on_calc(self):
        try:
            tf = self.bd.reduce()
            self.current_tf = tf
        except Exception as e:
            return messagebox.showerror("Erro", str(e))

        num, den = tf.num[0][0], tf.den[0][0]
        ne = sum(c*s_sym**i for i, c in enumerate(reversed(num)))
        de = sum(c*s_sym**i for i, c in enumerate(reversed(den)))
        tex = sp.latex(sp.simplify(ne/de))

        self.ax_tf.clear()
        self.ax_tf.text(0.1, 0.5, f"$G(s)={tex}$", size=14, color='#0A2667')
        self.ax_tf.axis('off')
        self.ax_tf.set_facecolor('white')
        self.canvas_tf.draw()

    def _plot_bode(self):
        if not hasattr(self, 'current_tf') or self.current_tf is None:
            return messagebox.showwarning("Aviso", "Calcule G(s) primeiro!")
            
        self.fig_plot.clf()
        self.fig_plot.patch.set_facecolor('white')
        
        # Cria subplots para magnitude e fase
        ax1 = self.fig_plot.add_subplot(211)
        ax2 = self.fig_plot.add_subplot(212)
        
        # Configura cores dos eixos
        for ax in [ax1, ax2]:
            ax.set_facecolor('white')
            for spine in ax.spines.values():
                spine.set_color('#0A2667')
            ax.tick_params(axis='x', colors='#0A2667')
            ax.tick_params(axis='y', colors='#0A2667')
            ax.yaxis.label.set_color('#0A2667')
            ax.xaxis.label.set_color('#0A2667')
            ax.title.set_color('#0A2667')
        
        # Plota o diagrama de Bode com cor azul
        ctl.bode_plot(self.current_tf, dB=True, Hz=False, deg=True, 
                     omega_limits=(0.1, 1000), ax=(ax1, ax2),
                     color='#3A5FCD')  # Azul médio
        
        ax1.set_title('Diagrama de Bode')
        ax1.grid(True, which='both', linestyle='--', alpha=0.7, color='#D6E4FF')
        ax2.grid(True, which='both', linestyle='--', alpha=0.7, color='#D6E4FF')
        
        self.fig_plot.tight_layout()
        self.canvas_plot.draw()

    def _plot_step(self):
        if not hasattr(self, 'current_tf') or self.current_tf is None:
            return messagebox.showwarning("Aviso", "Calcule G(s) primeiro!")
            
        self.fig_plot.clf()
        self.fig_plot.patch.set_facecolor('white')
        ax = self.fig_plot.add_subplot(111)
        ax.set_facecolor('white')
        
        # Configura cores dos eixos
        for spine in ax.spines.values():
            spine.set_color('#0A2667')
        ax.tick_params(axis='x', colors='#0A2667')
        ax.tick_params(axis='y', colors='#0A2667')
        ax.yaxis.label.set_color('#0A2667')
        ax.xaxis.label.set_color('#0A2667')
        ax.title.set_color('#0A2667')
        
        # Calcula a resposta ao degrau
        T, y = ctl.step_response(self.current_tf)
        
        # Plota a resposta em azul
        ax.plot(T, y, color='#3A5FCD', linewidth=2)
        ax.set_title("Resposta ao Degrau")
        ax.set_xlabel("Tempo (s)", color='#0A2667')
        ax.set_ylabel("Saída", color='#0A2667')
        ax.grid(True, linestyle='--', alpha=0.7, color='#D6E4FF')
        
        self.fig_plot.tight_layout()
        self.canvas_plot.draw()

    def _export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            filetypes=[("PDF", "*.pdf")])
        if not path:
            return

        # Salva as figuras temporariamente
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp1, \
             tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp2:
            
            graph_png = tmp1.name
            eq_png = tmp2.name
            
            self.fig_graph.savefig(graph_png, dpi=300, bbox_inches='tight', facecolor='white')
            self.fig_tf.savefig(eq_png, dpi=300, bbox_inches='tight', facecolor='white')

            # Cria o PDF
            c = pdf_canvas.Canvas(path, pagesize=letter)
            w, h = letter
            
            # Adiciona a equação
            eq_im = ImageReader(eq_png)
            ew, eh = eq_im.getSize()
            scale = min((w * 0.9) / ew, (h * 0.2) / eh)
            c.drawImage(eq_png, (w - ew*scale)/2, h - eh*scale - 40, 
                       width=ew*scale, height=eh*scale)
            
            # Adiciona o diagrama
            dg_im = ImageReader(graph_png)
            gw, gh = dg_im.getSize()
            scale = min((w * 0.9) / gw, (h * 0.6) / gh)
            c.drawImage(graph_png, (w - gw*scale)/2, h - eh*scale - gh*scale - 80, 
                       width=gw*scale, height=gh*scale)
            
            c.showPage()
            c.save()

        messagebox.showinfo("Sucesso", f"PDF salvo em:\n{path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BlockDiagramAcadApp(root)
    root.mainloop()