# Supply & Demand Order Blocks [JOAT] — MT5

Konversi dari Pine Script v6 oleh © officialjackofalltrades, berlisensi Mozilla Public License 2.0: https://mozilla.org/MPL/2.0/ . Atribusi dan pemberitahuan lisensi dipertahankan dalam sumber MQ5. Indikator ini tidak membuka order.

## File dan pemasangan

- SupplyDemandJOAT.ex5: indikator siap dipasang.
- SupplyDemandJOAT.mq5: kode sumber yang dapat diedit di MetaEditor.
- SupplyDemandJOAT.compile.log: hasil kompilasi.

1. Di terminal MT5 pilihan Anda, buka File > Open Data Folder.
2. Salin file EX5 ke folder MQL5\Indicators. MQ5 boleh ikut disalin.
3. Di Navigator > Indicators, klik kanan > Refresh.
4. Tarik SupplyDemandJOAT ke chart.
5. Aktifkan Chart Shift dan sisakan ruang kanan agar label Entry/SL/TP terlihat. Gunakan chart candlestick dengan latar gelap untuk palet asli.

## Visualisasi di chart

| Tampilan | Arti |
| --- | --- |
| Zona cyan bertuliskan Demand | Seluruh high–low candle bearish terakhir sebelum displacement naik |
| Zona magenta bertuliskan Supply | Seluruh high–low candle bullish terakhir sebelum displacement turun |
| Garis ungu | EMA tren, bawaan 50 |
| Candle cyan / magenta | Close di atas / di bawah EMA, bukan arah body candle |
| Panah dan teks BUY / SELL | Rejection zona yang memenuhi umur, tren, dan jarak antarsinyal |
| Kotak magenta | Area risiko dari Entry ke SL |
| Kotak hijau | Area reward dari Entry ke TP3 |
| Garis solid / putus / titik | Entry / SL / TP; harga tertulis di ujung kanan |
| Dashboard | Nearest OB, jumlah zona, book tilt, tren, conviction, sinyal, Win (TP1) |

Zona memudar berdasarkan kekuatan displacement dan umur. Ekstensi zona mengikuti bar paling kanan. Grafik trade menampilkan sinyal paling baru dan tetap terlihat setelah trade simulasi selesai, seperti sumber. Trend tint hanya digambar pada bagian chart yang terlihat dan diperbarui pada kalkulasi berikutnya setelah scroll/zoom. Warna transparan Pine didekati dengan pencampuran warna terhadap latar chart, karena rectangle MT5 memakai warna solid.

## Logika yang dipertahankan

- Displacement: selisih close dengan close 2 bar sebelumnya lebih besar daripada 1,5 ATR Wilder/RMA 14. EMA dihitung dengan seed close pertama; ATR memakai seed rata-rata true range pertama, sesuai Pine.
- Deteksi hanya ketika kondisi displacement baru berubah menjadi aktif. FVG opsional: low > high dua bar lalu untuk bullish, high < low dua bar lalu untuk bearish.
- Cari candle berlawanan terdekat dari offset DisplacementBars sampai DisplacementBars+3. Tidak ada syarat tambahan break of structure.
- Demand dihapus bila close di bawah dasar; supply dihapus bila close di atas puncak. Sentuhan wick saja tidak menghapus zona. Maksimum bawaan 12 zona; yang tertua dibuang dahulu.
- BUY: low <= puncak demand, close > dasar demand, candle bullish, umur zona minimal 2 bar, serta close > EMA bila filter aktif. SELL adalah kebalikannya.
- Umur zona dihitung dari candle asal, bukan saat zona terdeteksi. Kondisi sentuhan dipertahankan persis dari sumber; tidak ditambah syarat overlap rentang candle. Zona boleh memberi sinyal lagi; tidak diberi tanda sekali pakai.
- Pemindaian dari zona terbaru ke terlama; bila beberapa zona memenuhi, zona terakhir yang dipindai menentukan level risiko. Jarak antarsinyal bawaan 8 bar.
- Entry = close candle sinyal. SL = dasar demand - 0,25 ATR untuk BUY atau puncak supply + 0,25 ATR untuk SELL. TP bawaan 1R, 2R, 3R.
- Conviction adalah skor formula sumber, bukan probabilitas keuntungan. Nearest OB adalah jarak harga ke titik tengah zona, bukan ke tepi zona. Book tilt menghitung jumlah zona, bukan volume order book broker.

## Perbedaan dan pengaturan

ClosedBarSignals=true adalah bawaan versi MT5: zona, sinyal, dan statistik memakai candle selesai. EMA dan warna candle berjalan tetap diperbarui setiap tick. Dashboard menampilkan keadaan candle terakhir yang selesai. Pine sumber tidak memiliki pembatas barstate.isconfirmed; karena itu sinyal intrabar pada sumber dapat berubah, meskipun komentarnya menyebut non-repainting.

Untuk evaluasi candle berjalan seperti Pine, pilih ClosedBarSignals=false. Indikator mengulang simulasi dari histori pada setiap tick agar perubahan intrabar tidak menumpuk state. Mode ini lebih berat, dan sinyal/objek/statistik dapat berubah sebelum candle ditutup.

HistoryBars=10000 membatasi periode pemrosesan zona dan statistik; EMA/ATR tetap dipanaskan dari seluruh histori yang dimuat. HistoryBars=0 memproses seluruh histori. Perbedaan jumlah bar, feed broker, sesi, dan OHLC antara MT5 dan TradingView dapat menghasilkan sinyal berbeda. Hasil simulasi dapat berubah ketika histori dimuat ulang.

ShowDashboard, DashboardPosition (5 posisi), DashboardFontSize, dan DashboardBackground mengatur panel. ShowEMA, ColorCandles, ShowTrendTint, ShowTradeBoxes mengatur elemen chart. TP harus positif dan berurutan TP1 <= TP2 <= TP3 pada versi ini.

## Statistik Win (TP1)

Statistik mengikuti sumber: setiap sinyal membuka satu trade simulasi; evaluasi target dimulai pada candle setelah sinyal. TP1 dihitung menang; SL dihitung kalah. Jika TP1 dan SL tersentuh dalam candle yang sama, TP1 diprioritaskan. Jika sinyal baru datang ketika trade sebelumnya belum selesai, trade sebelumnya dihitung kalah sebelum trade baru dimulai. Ini dapat berbeda dari urutan tick nyata; spread, komisi, slippage, dan eksekusi tidak dimodelkan. TP2/TP3 hanya target visual, tidak dipakai dalam win-rate.

## Alert dan buffer

PopupAlerts, PushAlerts, SoundAlerts bawaan false. AlertNewBlocks menambahkan peringatan displacement baru, seperti alert sumber; candle berlawanan belum tentu ditemukan untuk membentuk zona. Alert sinyal diprioritaskan bila keduanya terjadi bersamaan. Tidak mengirim ulang alert historis saat pemasangan; maksimum satu alert per candle. Push membutuhkan konfigurasi Notifications di MT5.

Buffer iCustom: 0 EMA, 1 BUY (posisi panah), 2 SELL (posisi panah), 3–6 OHLC candle berwarna, 7 indeks warna (0 cyan, 1 magenta, 2 netral). Buffer sinyal berisi EMPTY_VALUE bila tidak ada sinyal. Angka buffer BUY/SELL bukan harga entry; entry adalah close candle sinyal.

## Validasi

MetaEditor berhasil mengompilasi dengan 0 errors dan 0 warnings. Belum dilakukan uji visual pada terminal MT5 atau perbandingan bar demi bar terhadap TradingView. Logika dan visual tersedia dalam indikator, tetapi kesamaan tampilan dan sinyal lintas platform belum diverifikasi lewat pengujian tersebut.

Referensi rendering candle MT5: https://www.mql5.com/en/docs/customind/indicators_examples/draw_color_candles .
