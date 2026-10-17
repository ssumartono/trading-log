# EMA SMA Signal Only v1.10

File EMASMA_PineProfitGuide.mq5/ex5 dipertahankan agar mudah mengganti versi sebelumnya. Isi terbaru sepenuhnya Signal Only, bukan Profit Protection.

- BUY saat EMA 9 candle sebelumnya <= SMA 20 lalu EMA candle selesai > SMA.
- SELL saat EMA candle sebelumnya >= SMA lalu EMA candle selesai < SMA.
- Panah hanya pada candle selesai; tidak ada konfirmasi candle tambahan atau filter SMA slope.
- EMA biru, SMA putih; panel sinyal terakhir, waktu candle server, dan Close sinyal.
- Tanpa posisi simulasi, proteksi, entry line, stop/trailing, EXIT marker, pembacaan posisi broker atau transaksi otomatis.
- Popup default ON; push default OFF dan membutuhkan konfigurasi Notifications MT5. Alert historis saat pemasangan tidak dikirim.
- Panah historis/sinyal terakhir bukan instruksi mengejar entry lama. Sinyal tidak menjamin arah candle berikutnya.

Instalasi: lepaskan indikator Pine Profit Guide lama dari chart (Ctrl+I), ganti EX5 di MQL5/Indicators dan pasang ulang. Periksa nama EMA SMA Signal Only v1.10. Jangan menumpuk versi lama. Garis oranye/tanda silang dari versi lama hilang setelah indikator lama dilepas. Channel atau objek milik indikator lain serta garis entry/SL/TP transaksi pengguna tidak dihapus atau diubah.

Input: EMA9/SMA20, Popup/Push, HistoryBars2000, PanelX16/PanelY28/PanelScale100 (75–150 persen). Tidak memerlukan Algo Trading. EA otomatis yang masih terpasang perlu dilepas sendiri jika ingin seluruh eksekusi manual.

Kompilasi 0 errors, 0 warnings. Pemeriksaan source memastikan tidak ada logika simulasi/proteksi/order; tampilan dan alert belum diuji runtime pada terminal pengguna.
