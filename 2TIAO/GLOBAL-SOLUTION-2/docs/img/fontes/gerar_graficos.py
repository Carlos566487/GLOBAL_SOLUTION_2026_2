"""Gera os gráficos de docs/img/graficos/.

Uso (a partir da raiz do repositório):
    pip install matplotlib openpyxl
    python 2TIAO/GLOBAL-SOLUTION-2/docs/img/fontes/gerar_graficos.py

Fontes dos números:
- golden_set_tipos, recolhimentos_trimestre, recolhimentos_motivos: data/Golden_Set_Recall.json e data/Dataset_Recall_Anvisa.xlsx
- extracao_por_campo, extracao_por_tipo: docs/resultados_extracao.md (execução de 17/11/2026)
- ocr_desfechos, ocr_por_campo: docs/resultados_ocr.md (regra alinhada, 18/11/2026)
- motor_escala: src/backend/tests/test_cenarios_demo.py (execução de 19/11/2026)
Paleta: azul #2a78d6 e laranja #eb6834 (validadas para daltonismo), cinza neutro.
"""
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[3]          # 2TIAO/GLOBAL-SOLUTION-2
OUT_DIR = RAIZ / "docs" / "img" / "graficos"
XLSX = RAIZ / "data" / "Dataset_Recall_Anvisa.xlsx"
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
OUT=str(OUT_DIR)+"/"
B1,B2,GR,INK,INK2="#2a78d6","#eb6834","#b5b3ad","#0b0b0b","#52514e"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.edgecolor":"#d9d8d4","axes.labelcolor":INK2,
 "xtick.color":INK2,"ytick.color":INK2,"axes.spines.top":False,"axes.spines.right":False,"figure.dpi":200,"axes.titleweight":"bold","axes.titlesize":13,"axes.titlelocation":"left"})
def save(f,n):
  ax=f.axes[0]; t=ax.get_title(loc="left"); ax.set_title("",loc="left"); f.suptitle(t,x=0.012,ha="left",fontweight="bold",fontsize=12,color=INK); f.tight_layout(); f.savefig(OUT+n,facecolor="white"); plt.close(f)

# 1 golden set tipos
f,ax=plt.subplots(figsize=(7,3.2))
t=["lista","todos","data_corte","sem regra (null)","sufixo"]; v=[16,2,1,1,0]
ax.barh(t[::-1],v[::-1],color=B1,height=0.55)
for i,x in enumerate(v[::-1]): ax.text(x+0.3,i,str(x) if x else "0 (só teste sintético)",va="center",color=INK)
ax.set_title("Golden set: 20 recolhimentos reais por tipo de regra de lote"); ax.set_xlabel("recolhimentos"); ax.xaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True); ax.set_xlim(0,19); ax.set_xticks(range(0,19,2))
save(f,"golden_set_tipos.png")

# 2 extração por campo
campos=["Regra de lote","Produto","Marca","Fabricante","CNPJ"]
g=[96,65,46,88,54]; r=[100,100,46,100,100]
import numpy as np; x=np.arange(len(campos)); w=0.36
f,ax=plt.subplots(figsize=(8,3.8))
b1=ax.bar(x-w/2-0.01,g,w,color=B1,label="contra o gabarito (n=26)")
b2=ax.bar(x+w/2+0.01,r,w,color=B2,label="sobre o recuperável no texto")
for bars in (b1,b2):
  for b in bars: ax.text(b.get_x()+b.get_width()/2,b.get_height()+1.5,f"{b.get_height():.0f}%",ha="center",fontsize=9,color=INK)
ax.set_xticks(x,campos); ax.set_ylim(0,112); ax.set_ylabel("acerto por registro (%)"); ax.yaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True)
ax.set_title("Extrator LLM (Gemini, temp. 0): acerto por campo nos 26 registros reservados")
ax.legend(frameon=False,loc="lower left",fontsize=9,ncol=2,bbox_to_anchor=(0,-0.32))
save(f,"extracao_por_campo.png")

# 3 OCR desfechos
f,ax=plt.subplots(figsize=(7.5,3.2))
cat=["Erro confiante\n(pior caso)","Acerto conclusivo","Pendente correto\n(sem lote legível)","Pendente com\nlote legível"]; vv=[0,0,5,7]
cols=[B2,B1,GR,GR]
ax.barh(cat,vv,color=cols,height=0.55)
for i,x in enumerate(vv): ax.text(x+0.15,i,f"{x}/12",va="center",color=INK)
ax.set_xlim(0,9); ax.set_title("Leitor da embalagem: desfecho em 12 fotos reais (limiar 0,8)"); ax.set_xlabel("fotos"); ax.xaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True)
save(f,"ocr_desfechos.png")

# 4 OCR por campo
f,ax=plt.subplots(figsize=(7,3))
cc=["EAN (código de barras)","Lote","Validade","Data de fabricação"]; ok=[6,4,1,0]; tot=[6,7,5,1]
pct=[a/b*100 for a,b in zip(ok,tot)]
ax.barh(cc[::-1],pct[::-1],color=B1,height=0.55)
for i,(a,b) in enumerate(list(zip(ok,tot))[::-1]): ax.text(a/b*100+1.5,i,f"{a}/{b}  ({a/b*100:.0f}%)",va="center",color=INK)
ax.set_xlim(0,125); ax.set_xticks([0,25,50,75,100]); ax.set_title("Leitor da embalagem: campos lidos corretamente (0 lidos errado)"); ax.set_xlabel("% das fotos em que o campo existe")
ax.xaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True)
save(f,"ocr_por_campo.png")

# 5 motor escala
f,ax=plt.subplots(figsize=(7,2.8))
lab=["Matches (lote na lista)","Pendentes (lote ausente)","Sem match"]; obs=[501,126,373]
ax.barh(lab[::-1],obs[::-1],color=[GR,B2,B1][::-1] if False else [GR,B2,B1],height=0.55)
for i,x in enumerate(obs[::-1]): ax.text(x+8,i,f"{x}  (esperado {x})",va="center",color=INK)
ax.set_xlim(0,820); ax.set_title("Motor de regras: 1.000 recebimentos simulados, 20 lojas, 53 ms"); ax.set_xlabel("recebimentos"); ax.xaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True)
save(f,"motor_escala.png")


# ---- gráficos do problema e da extração por tipo ----
import openpyxl, collections
def save2(f,ax,title,n):
  f.suptitle(title,x=0.012,ha="left",fontweight="bold",fontsize=12,color=INK); f.tight_layout(); f.savefig(OUT+n,facecolor="white"); plt.close(f)
wb=openpyxl.load_workbook(XLSX,read_only=True)
rows=list(wb['Alertas'].iter_rows(values_only=True))[1:]
rows=[r for r in rows if r[0]]
# linha do tempo por trimestre
c=collections.Counter(f"{r[1].year}-T{(r[1].month-1)//3+1}" for r in rows)
qs=["2025-T3","2025-T4","2026-T1","2026-T2","2026-T3","2026-T4"]
f,ax=plt.subplots(figsize=(8,3.4))
v=[c.get(q,0) for q in qs]
ax.bar([q.replace("-"," ") for q in qs],v,color=B1,width=0.55)
for i,x in enumerate(v): ax.text(i,x+0.15,str(x),ha="center",color=INK)
ax.set_ylabel("recolhimentos"); ax.yaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True); ax.set_ylim(0,max(v)+2)
ax.text(5,v[5]+1.1,"até 16/11",ha="center",fontsize=8.5,color=INK2)
save2(f,ax,f"Recolhimentos de alimentos no golden set por trimestre (n={len(rows)})","recolhimentos_trimestre.png")
# motivos
cat={"Contaminação microbiológica":["crystal","aptamil","la-vaquita","italy","kf","militao","jms","dviez","nestle-formulas"],
"Ingrediente ou aditivo não autorizado":["neovite","ubon","vaidosa","bento","equaliv"],
"Falhas de fabricação / estabilidade":["agua-da-serra","sanibras","nutra"],
"Corpo estranho (vidro, matérias estranhas)":["granoro","de-marchi"],
"Alergênico não declarado":["cecco"]}
ids={r[0] for r in rows}; assert sum(len(x) for x in cat.values())==len(ids) and set(sum(cat.values(),[]))==ids
labs=list(cat); vals=[len(cat[k]) for k in labs]
f,ax=plt.subplots(figsize=(8,3.4))
ax.barh(labs[::-1],vals[::-1],color=B1,height=0.55)
for i,x in enumerate(vals[::-1]): ax.text(x+0.15,i,f"{x}  ({x/len(ids)*100:.0f}%)",va="center",color=INK)
ax.set_xlim(0,12); ax.set_xlabel("recolhimentos"); ax.xaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True)
save2(f,ax,"Motivo sanitário dos 20 recolhimentos do golden set","recolhimentos_motivos.png")
# extração por tipo de regra
t=["lista","data_corte","sem regra (null)","todos"]; ok=[23,1,1,0]; n=[23,1,1,1]
f,ax=plt.subplots(figsize=(8,3))
pct=[a/b*100 for a,b in zip(ok,n)]
ax.barh(t[::-1],pct[::-1],color=[B2 if p<100 else B1 for p in pct[::-1]],height=0.55)
for i,(a,b) in enumerate(list(zip(ok,n))[::-1]):
  ax.text(a/b*100+1.5,i,f"{a}/{b}"+("  → virou verificacao_pendente" if a<b else ""),va="center",color=INK)
ax.set_xlim(0,150); ax.set_xticks([0,25,50,75,100]); ax.set_xlabel("% de registros com a regra completa correta"); ax.xaxis.grid(True,color="#eeede9"); ax.set_axisbelow(True)
save2(f,ax,"Extrator LLM: regra de lote correta por tipo (26 registros reservados)","extracao_por_tipo.png")
print(f"gráficos gerados em {OUT_DIR}")
