# Perbaikan empat temuan audit

1. Kalender menggunakan tanggal hari ini dalam WIB. Log, candle, tick, dan konteks market AI memakai konversi timestamp yang sama. Pengaturan setiap broker menyediakan basis UTC (standar MT5), atau waktu server dengan offset dalam menit. Nilai lama tidak ditebak; pengguna perlu memeriksa kesesuaiannya dengan terminal lalu menandai konfirmasi. Perubahan konfigurasi diterapkan ke data sumber saat penyimpanan/sinkronisasi tanpa menghapus evaluasi manual. Offset tetap perlu diperiksa kembali jika broker mengganti zona waktu musiman.
2. Profit (Max) hanya mencari nilai positif; Loss (Max) hanya mencari nilai negatif. Jika tidak ada hasil yang sesuai, kartu menampilkan nilai kosong tanpa tautan detail yang keliru.
3. Checkpoint saldo tersimpan terpisah di SQLite. Akun lama mulai dari snapshot MT5 terakhir yang tersedia. Akun baru mengestimasi saldo awal sekali saat impor pertama, lalu mempertahankannya. Selisih saldo checkpoint, selisih terhadap log, ticket yang belum diproyeksikan, dan backfill historis ditandai untuk ditinjau. Checkpoint pertama tidak membuktikan bahwa riwayat sebelum checkpoint lengkap.
4. Status per akun menyimpan percobaan terbaru, hasil tes koneksi/sinkronisasi, kesalahan, waktu berhasil terakhir, jumlah deal baru/diperbarui, ticket terbaru, dan hasil rekonsiliasi. Dashboard dan Pengaturan membaca status setiap lima detik tanpa mengganti formulir edit. Gagal pada satu akun tidak menghentikan jadwal akun berikutnya. Satu terminal MT5 tetap hanya melayani akun yang sedang login.

Pengujian: `python -m unittest discover -v`, `node mockup/check-audit-fixes.cjs`, `node mockup/check-performance.cjs`, `node mockup/check-period-summary.cjs`, `node mockup/check-waterfall.cjs`.

Cadangan SQLite dibuat sebelum server dijalankan ulang. Konfigurasi dan API key AI masih disimpan dalam memori server, sehingga perlu diisi ulang setelah restart.
