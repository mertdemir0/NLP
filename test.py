import numpy as np
import matplotlib.pyplot as plt
import ternary

# Piper diyagramı için veriler (katyon ve anyon yüzdeleri)
kuyular = ["TEAM-1", "TEAM-4", "TEAM-6"]

# Katyonlar: Na+K, Ca, Mg (%)
katyonlar = {
    "TEAM-1": [50, 30, 20],  # Na+K, Ca, Mg
    "TEAM-4": [45, 35, 20],
    "TEAM-6": [55, 25, 20]
}

# Anyonlar: Cl, SO4, HCO3+CO3 (%)
anyonlar = {
    "TEAM-1": [40, 20, 40],  # Cl, SO4, HCO3+CO3
    "TEAM-4": [35, 25, 40],
    "TEAM-6": [30, 20, 50]
}

# Piper diyagramı için figür ve eksenler oluşturuluyor
fig = plt.figure(figsize=(10, 8))

# Katyon Üçgeni
ax1 = fig.add_axes([0.05, 0.1, 0.4, 0.4])
ax1.set_title("Katyon Üçgeni")
tax1 = ternary.TernaryAxesSubplot(ax=ax1)
tax1.boundary(linewidth=1.5)
tax1.gridlines(color="gray", multiple=10)
tax1.ticks(axis='lbr', multiple=20, offset=0.02)

for kuyu, (na_k, ca, mg) in katyonlar.items():
    tax1.scatter([[na_k, ca, mg]], marker="o", label=kuyu)

tax1.legend()
tax1.show()

# Anyon Üçgeni
ax2 = fig.add_axes([0.55, 0.1, 0.4, 0.4])
ax2.set_title("Anyon Üçgeni")
tax2 = ternary.TernaryAxesSubplot(ax=ax2)
tax2.boundary(linewidth=1.5)
tax2.gridlines(color="gray", multiple=10)
tax2.ticks(axis='lbr', multiple=20, offset=0.02)

for kuyu, (cl, so4, hco3_co3) in anyonlar.items():
    tax2.scatter([[cl, so4, hco3_co3]], marker="o", label=kuyu)

tax2.legend()
tax2.show()

# Orta Kristal Alan (Karışım Bölgesi)
ax3 = fig.add_axes([0.3, 0.55, 0.4, 0.4])
ax3.set_title("Piper Diyagramı - Karışım Bölgesi")
ax3.set_xlim(-1, 1)
ax3.set_ylim(-1, 1)

for kuyu in kuyular:
    x = (katyonlar[kuyu][0] - anyonlar[kuyu][0]) / 100
    y = (katyonlar[kuyu][1] - anyonlar[kuyu][1]) / 100
    ax3.scatter(x, y, label=kuyu, s=80)

ax3.axhline(0, color="black", linewidth=1)
ax3.axvline(0, color="black", linewidth=1)
ax3.legend()
ax3.grid()

plt.show()