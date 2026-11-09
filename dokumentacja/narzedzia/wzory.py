import sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
out=sys.argv[1]
F={
"wzor_tsp": r"$L(\pi)=\sum_{k=0}^{n-1} d_{\pi_k\,\pi_{k+1}} + d_{\pi_n\,\pi_0}\;\rightarrow\;\min,\qquad \pi_0=0$",
"wzor_p": r"$p_{ij}^{k}=\dfrac{[\tau_{ij}]^{\alpha}\,[\eta_{ij}]^{\beta}}{\sum_{l\in N_i^k}[\tau_{il}]^{\alpha}\,[\eta_{il}]^{\beta}},\qquad \eta_{ij}=\dfrac{1}{d_{ij}}$",
"wzor_tau": r"$\tau_{ij}\leftarrow(1-\rho)\,\tau_{ij}+\sum_{k=1}^{m}\Delta\tau_{ij}^{k}+e\cdot\Delta\tau_{ij}^{best}$",
"wzor_dtau": r"$\Delta\tau_{ij}^{k}=\begin{cases}Q/L_k & \mathrm{gdy\ mrowka}\ k\ \mathrm{przeszla\ krawedzia}\ (i,j)\ 0 & \mathrm{w\ przeciwnym\ razie}\end{cases}$",
}
F["wzor_dtau"]=r"$\Delta\tau_{ij}^{k}=\dfrac{Q}{L_k}$"
for name,tex in F.items():
    fig=plt.figure(figsize=(0.01,0.01)); fig.text(0,0,tex,fontsize=17)
    fig.savefig(f"{out}/{name}.png",dpi=200,bbox_inches="tight",pad_inches=0.06,transparent=False,facecolor="white"); plt.close(fig)
    from PIL import Image; im=Image.open(f"{out}/{name}.png"); print(name, im.size)
