# Range Oscillator pada Live Chart

Implementasi mengikuti `indicators/RangeOscillator.mq5` versi 1.10 dan panduan lokalnya, bukan osilator highest/lowest generik. Rumus berada di `range_oscillator.py`.

- Default: MinimumRangeLength 50, RangeWidthMultiplier 2, NumberOfHeatLevels 2, MinimumTouchesPerLevel 1.
- Mean berbobot perubahan relatif close; ATR Wilder RMA 2000, dengan fallback RMA 200 sebelum tersedia 2000 candle.
- Warna heatmap, histogram shading, dan level +100 / 0 / -100 mengikuti adaptasi MT5 lokal. Osilator dapat melampaui batas referensi.
- Buy menandai penembusan ke atas +100; Sell menandai penembusan ke bawah -100. Tanda hanya dibuat pada candle selesai dan memakai offset 30 point, sesuai default sumber lokal.
- Panel volume dihilangkan. Histogram pada panel bawah adalah shading osilator, bukan volume. Panel harga tetap memiliki garis Entry/SL/TP.

Backend meminta sampai 3000 candle untuk pemanasan perhitungan, lalu mengirim 300 candle terakhir beserta data osilator dan sinyal pada rentang waktu yang sama. Riwayat kurang dari 200 candle atau bobot perubahan harga nol menghasilkan data kosong, bukan angka nol buatan. Nilai candle berjalan tetap dapat berubah.

Waktu, pan, zoom, crosshair, tema, dan screenshot memakai satu chart dengan dua pane sehingga sumbu waktu tetap sejajar. Aritmetika seed ATR dan mean, warmup, penembusan candle selesai, warna, serta penyelarasan waktu diuji otomatis. Tampilan juga diperiksa dengan candle demonstrasi. Belum ada pembandingan buffer bar per bar terhadap indikator di terminal MT5; perbedaan panjang/awal riwayat dapat memengaruhi seed ATR dan hasil.

Original Pine copyright Zeiierman. Adaptasi lokal MT5 dan port perhitungan ini memakai CC BY-NC-SA 4.0: https://creativecommons.org/licenses/by-nc-sa/4.0/ . Atribusi ditampilkan pada Live Chart.

Pengujian: `python -m unittest test_range_oscillator test_live_chart -v`, `node --test test_range_oscillator_ui.cjs`, dan `node mockup/check-chart-levels.cjs`.
