import matplotlib.pyplot as plt
import pandas as pd
 
# Meteoroloji verileri (Aksaray 1929-2024)
months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
 
# Aylık toplam yağış miktarı (mm)
rainfall = [40.4, 34.4, 41.2, 45.3, 43.6, 29.1, 7.0, 5.7, 12.3, 23.3, 31.5, 45.8]
 
# Ortalama sıcaklık (°C)
avg_temp = [0.6, 2.1, 6.4, 11.6, 16.2, 20.3, 23.6, 23.4, 18.8, 13.4, 7.3, 2.7]
 
# Ortalama güneşlenme süresi (saat)
sunshine = [4.5, 5.7, 7.1, 7.9, 9.1, 11.1, 12.1, 11.5, 9.7, 7.1, 5.0, 3.2]
 
# Grafik oluşturma
fig, ax1 = plt.subplots(figsize=(10,5))
 
# Yağış için çubuk grafik
ax1.bar(months, rainfall, color='b', alpha=0.6, label="Aylık Yağış (mm)")
ax1.set_ylabel("Yağış (mm)", color='b')
ax1.set_xlabel("Aylar")
ax1.tick_params(axis='y', labelcolor='b')
 
# İkincil eksen (sıcaklık ve güneşlenme süresi)
ax2 = ax1.twinx()
ax2.plot(months, avg_temp, color='r', marker='o', label="Ortalama Sıcaklık (°C)")
ax2.plot(months, sunshine, color='g', marker='s', label="Güneşlenme Süresi (saat)")
ax2.set_ylabel("Sıcaklık (°C) & Güneşlenme Süresi (saat)", color='black')
ax2.tick_params(axis='y', labelcolor='black')
 
# Başlık ve açıklamalar
fig.suptitle("Aksaray 1929-2024 Meteoroloji Verileri", fontsize=12)
ax1.legend(loc='upper left')
ax2.legend(loc='upper right')
 
# Grafiği kaydetme
fig.savefig("Aksaray_Meteoroloji_Verileri.png", dpi=300)
 
# Grafiği gösterme
plt.show()