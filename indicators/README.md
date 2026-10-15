# Range Filter untuk MetaTrader 5

`RangeFilter.mq5` adalah source; `RangeFilter.ex5` adalah indikator siap pakai.
Konversi dari Pine v5 yang diberikan pengguna: original @DonovanWall,
adaptasi @guikroth, publikasi v5 @tvenn.

## Instalasi

1. Di terminal MT5 tujuan, pilih File > Open Data Folder.
2. Salin RangeFilter.ex5 (dan source jika diperlukan) ke MQL5/Indicators.
3. Di Navigator > Indicators, klik kanan > Refresh.
4. Tarik RangeFilter ke chart. Gunakan M5 untuk konfigurasi awal yang diberikan.

## Pengaturan

- Source: Close sebagai default; tersedia pilihan applied price MT5.
- SamplingPeriod: 100; RangeMultiplier: 3.0.
- ClosedBarSignals: true menampilkan panah dan alert sesudah candle selesai.
  Ubah ke false untuk perilaku intrabar Pine asli; sinyal candle berjalan bisa hilang.
- ShowBands / FillBands / ColorCandles mengatur tampilan.
- ArrowOffsetPoints: jarak panah dari high/low dalam point simbol, bukan pip.
- PopupAlert / PushAlert / SoundAlert: default mati. Push memerlukan konfigurasi
  Notifications pada MT5; sound menggunakan SoundFile.

## Logika

Range = EMA(EMA(abs(source - source sebelumnya), period), 2*period-1)
dikalikan multiplier. Filter menahan nilai sebelumnya sampai harga melampaui
range. Penghitung naik/turun mempertahankan arah saat filter datar.
Buy hanya muncul jika kondisi long mengikuti kondisi short; Sell kebalikannya.
Harga source yang sama dengan bar sebelumnya tidak memicu kondisi baru,
sesuai ekspresi Pine. Kondisi arah pertama hanya menginisialisasi state.

EMA dimulai dari perubahan harga pertama yang tersedia. Nilai filter awal
mengikuti nz(filter[1]) pada Pine. Riwayat awal dan harga broker yang berbeda
dapat menghasilkan nilai berbeda dari TradingView, terutama pada awal riwayat.

## Perbedaan tampilan dan alert

Panah menggantikan label teks Buy/Sell. Warna candle digambar sebagai overlay.
Fill MT5 menggunakan warna solid redup, bukan transparansi Pine.
Alert hanya untuk bar terbaru yang sesuai mode, maksimal sekali per waktu bar;
tidak mengirim ulang seluruh sinyal historis saat indikator dipasang.
Indikator mengikuti simbol dan timeframe chart, tidak mengunci M5/BTCUSDC.
Tidak membuka order dan tidak menyertakan kode strategi TP/SL yang dikomentari.

## Buffer untuk iCustom / EA (indeks mulai 0)

4 = filter, 6 = high target, 7 = low target, 8 = Buy, 9 = Sell.
Buffer sinyal berisi harga panah, atau EMPTY_VALUE jika tidak ada sinyal.
Dengan ClosedBarSignals=true, baca shift 1 untuk candle terakhir yang selesai.

## Validasi

Dikompilasi dengan MetaEditor MT5: 0 errors, 0 warnings (lihat compile.log).
Belum diuji secara visual pada chart atau dibandingkan bar per bar dengan
TradingView pada data OHLC yang sama.
