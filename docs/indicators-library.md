# Indicators Library

Menu Indicators Library menampilkan indikator dalam proyek. Range Oscillator sudah mendukung Live Chart. Range Filter, Liquidity Reaper, dan Supply Demand JOAT ditandai MT5 saja; berkas EX5 tidak dijalankan langsung di browser.

Live Chart tanpa pilihan tersimpan tampil tanpa indikator. Load menambahkan panel Range Oscillator dengan periode 2–500 dan multiplier 0.1–20. Beberapa konfigurasi bisa dimuat bersamaan, maksimal delapan. Hapus mengeluarkan satu panel; Hapus semua mengembalikan chart harga saja. Pilihan disimpan di browser per pengguna dan akun, terpisah dari riwayat transaksi.

API chart menerima daftar `indicators` dengan `id`, `type: range-oscillator`, `length`, dan `multiplier`. Daftar kosong melewati perhitungan indikator dan meminta 300 candle, sedangkan pilihan indikator meminta 3000 candle untuk pemanasan ATR. Setiap hasil diberi ID agar panel tidak tertukar. Data harga dan level posisi tetap ditampilkan. Detail rumus dan lisensi ada di range-oscillator-live-chart.md.

Untuk menambahkan jenis indikator berikutnya, diperlukan kalkulasi server, validasi parameter, entri registry library, dan renderer chart yang sesuai (panel atau overlay). Status MT5 saja tetap dipakai sampai adaptasi tersebut tersedia.
