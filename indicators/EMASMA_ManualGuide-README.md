# EMA/SMA Confirmed Manual v1.30

Indikator informatif MT5, bukan EA. Tidak ada transaksi, SL/TP atau trailing otomatis. Versi crossover langsung dicadangkan di EMASMA_SignalOnly_v1.20.mq5.

Aturan baru:
1. Crossover EMA 9/SMA 20 pada candle selesai membuat CALON BUY/SELL, ditandai titik kuning.
2. Hanya candle tepat berikutnya yang boleh mengonfirmasi. Buy membutuhkan Close > High candle calon, EMA > SMA dan SMA naik dari candle sebelumnya. Sell membutuhkan Close < Low calon, EMA < SMA dan SMA turun. Semua pembandingan ketat; sama dengan level tidak lolos.
3. Semua syarat harus terpenuhi setelah candle berikutnya selesai. Panah hijau/merah ENTRY muncul pada candle konfirmasi tersebut, bukan dipindahkan ke candle calon.
4. Jika satu syarat gagal, calon dibatalkan. Tidak menunggu candle lain untuk menghidupkan kembali calon lama. Pembatalan bukan sinyal entry berlawanan.
5. Jika crossover baru muncul pada candle yang membatalkan calon lama, crossover baru itu menjadi calon arah baru dan menunggu candle berikutnya.
6. Exit tetap acuan crossover berlawanan dari logika awal; dipisahkan dari konfirmasi entry. Indikator tidak membaca posisi atau mengeksekusi exit. Pembatalan calon entry lawan tidak membatalkan informasi crossover untuk exit.

Panel: status CALON / TERKONFIRMASI / DIBATALKAN, waktu calon, High/Low pembanding, hasil tiga syarat, entry terkonfirmasi terakhir dan petunjuk exit manual. Status tersimpan pada hasil calon terbaru sampai ada crossover baru, bukan izin mengejar entry historis. Panel menampilkan waktu candle server broker, bukan otomatis WIB.

Alert: calon default ON melalui InpAlertCandidates; entry terkonfirmasi mengikuti InpPopupAlerts (default true) dan InpPushAlerts (default false). Alert pembatalan opsional InpAlertCancelled=false. Tidak ada alert historis saat pasang/reset history. Push memerlukan pengaturan Notifications MT5.

Instalasi: salin EMASMA_ManualGuide.ex5 terbaru ke MQL5/Indicators, Refresh Navigator, lepaskan indikator lama dan pasang ulang. Periksa nama EMA SMA Confirmed Manual v1.30. Posisi panel diatur InpPanelX/Y dan skala 75–150 persen. Lepaskan EA lama jika ingin seluruh eksekusi manual.

Verifikasi di demo/Visual Tester:
- Titik kuning pada crossover tertutup, panah entry paling cepat satu candle kemudian.
- Buy Close di bawah/sama High calon dibatalkan meski candle hijau. Sell berlaku terbalik.
- Kemiringan SMA yang berlawanan/datar menggagalkan konfirmasi.
- Sinyal tidak muncul pada candle berjalan dan tidak dipindah ke masa lalu.
- Calon gagal tidak dikonfirmasi oleh candle kedua/ketiga sesudahnya tanpa cross baru.

Kompilasi MetaEditor 0 errors, 0 warnings. Tampilan/alert/runtime belum diuji di terminal pengguna. Filter membuat entry lebih lambat dan belum terbukti meningkatkan profitabilitas atau akurasi sebelum backtest.
