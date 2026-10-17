# Consolidation Range with Signals — MT5

Konversi Pine Script asli © Zeiierman. Lisensi CC BY-NC-SA 4.0:
https://creativecommons.org/licenses/by-nc-sa/4.0/
Hanya penggunaan nonkomersial; atribusi dan lisensi yang sama harus dipertahankan.

## Instalasi
1. MT5 > File > Open Data Folder.
2. Salin ConsolidationRange_Zeiierman.ex5 ke MQL5\Indicators.
3. Navigator > Indicators > Refresh, lalu tarik indikator ke chart.
4. Sediakan minimal 2.002 candle; disarankan lebih dari 3.000 untuk pemanasan ADX.
5. Lepas indikator versi lama lalu pasang ulang versi 1.10, atau tekan Reset pada Inputs agar pengaturan tampilan terbaru diterapkan. TP1, TP2 dan TP3 aktif secara default.

## Isi dan pengaturan
- Method: ADX_Method atau Volatility_Method, sesuai dua pilihan pada kode asli.
- RangePeriod 10, RangeMultiplier 1.8, ADXThreshold 17, ADXSmoothing 10.
- Lebar dasar: SMA 2.000 bar dari 2.618 * abs(high - low candle sebelumnya), dikali RangeMultiplier.
- Zona menampilkan filter, MID1–MID4, serta isian atas dan bawah.
- Entry berada pada harga close candle sinyal. SL dan TP dihitung dari nilai filter, bukan dari entry, mengikuti Pine asli.
- CooldownBars 20; panjang garis LevelLengthBars 20.
- ShowTargets, ShowSL, ShowTP1–ShowTP3 mengatur level.
- MaxSignalGroups membatasi jumlah kelompok garis untuk menjaga chart tetap ringan.
- ShowArrows menampilkan panah BUY/SELL.
- ClosedBarSignals=true: hanya candle selesai. false: candle berjalan dapat mengubah sinyal.
- PopupAlerts, PushAlerts, SoundAlerts awalnya mati. Push membutuhkan konfigurasi Notifications MT5.
- Alert historis saat indikator baru dipasang tidak dikirim.

## Perbedaan visual dan batas verifikasi
Versi 1.10 memakai kanvas dengan gradasi 12 lapis, garis zona bertingkat dan jeda antarzona tanpa sambungan diagonal. Label Entry/SL/TP memakai kotak berwarna dengan teks putih. Rendering menyesuaikan zoom, scroll dan ukuran chart. Warna gradasi menyesuaikan latar chart tanpa mengganti tema pengguna.

Default MaxSignalGroups=3 untuk mengurangi penumpukan; naikkan untuk melihat lebih banyak riwayat atau pilih 1 untuk sinyal terakhir saja. Label yang bertumpuk disembunyikan dengan prioritas sinyal terbaru; garis level tetap tersedia. Label di luar area chart tidak digambar. LabelFontSize dan LabelMinimumGap mengatur keterbacaan. ShowLevelPrices menambahkan harga pada label. ShowArrows=false secara default. Batas atas dan bawah mengikuti MID2/MID4 asli, bukan tambahan batas +/-r.

Perhitungan deteksi, entry, SL/TP dan cooldown tetap menggunakan logika versi sebelumnya. Perubahan ini berfokus pada tampilan.
Dengan ClosedBarSignals=true, candle berjalan sengaja tidak digambar hingga selesai. Data broker dan panjang riwayat dapat menghasilkan perbedaan dari TradingView.
Indikator tidak membuka order. Tidak ada dependensi indikator eksternal.
Kompilasi MetaEditor: 0 errors, 0 warnings. Pengujian visual/runtime di chart MT5 belum dilakukan.
Source MQ5 dan Pine asli disertakan agar logika dapat diaudit dan dikembangkan.
