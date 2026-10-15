# Liquidity Reaper [JOAT] untuk MT5

Source Pine asli: officialjackofalltrades, Mozilla Public License 2.0.
Source konversi mempertahankan pemberitahuan lisensi dan atribusi tersebut.

## Instalasi

1. Buka MT5 > File > Open Data Folder.
2. Salin `LiquidityReaper.ex5` ke folder `MQL5/Indicators`.
3. Pada Navigator > Indicators, klik kanan > Refresh.
4. Tarik LiquidityReaper ke chart simbol dan timeframe yang diinginkan.
5. Aktifkan Chart Shift jika label harga di sisi kanan terlalu dekat tepi chart.

`LiquidityReaper.mq5` adalah source yang dapat diedit dan dikompilasi dengan MetaEditor.
Indikator menampilkan setup; tidak membuka atau mengelola order.

## Cara membaca setup entry

- BUY: harga menembus swing low yang sudah terkonfirmasi, lalu dalam 1–3 candle berikutnya candle bullish ditutup di atas level pool.
- SELL: harga menembus swing high yang sudah terkonfirmasi, lalu dalam 1–3 candle berikutnya candle bearish ditutup di bawah level pool.
- Kedalaman wick minimal 25% dari range candle penembusan. Extreme terus diperbarui selama menunggu konfirmasi.
- Filter volume: volume candle konfirmasi minimal 1.1 kali SMA volume 20 candle, termasuk candle konfirmasi itu sendiri.
- Entry = close candle konfirmasi. Ini harga acuan, bukan jaminan harga eksekusi order berikutnya.
- SL default = entry dikurangi/ditambah ATR Wilder 14 × 1.5.
- TP1, TP2, TP3 = 1R, 2R, 3R dari entry.
- Hanya setup terbaru yang masih aktif memiliki garis entry/SL/TP serta area risiko/reward. Setup baru menggantikan setup sebelumnya. Versi 1.01 menyembunyikan seluruh garis dan area setup setelah selesai, sehingga tampilan berbeda dari Pine asli yang tetap menyimpan setup terakhir.
- Setup selesai ketika SL atau TP tertinggi yang diaktifkan tersentuh pada candle sesudah candle entry. Jika keduanya tersentuh dalam candle yang sama, dashboard menandai hasil ambigu; OHLC tidak menentukan urutannya.
- SwingStrength=8 berarti pivot baru terkonfirmasi sesudah 8 candle di sebelah kanan. Garis dapat dimulai pada candle pivot, tetapi pivot belum tersedia sebelum konfirmasi tersebut.
- Tanpa sweep yang valid, dashboard menampilkan status menunggu dan tidak memaksakan entry.
- Setelah setup selesai, dashboard menampilkan `MENUNGGU SETUP BARU` dan `Tidak ada setup entry aktif`. Harga entry/SL/TP lama tidak ditampilkan; alasan selesai tetap terlihat pada baris `Setup terakhir SELESAI`.
- Label `RIWAYAT BUY/SELL` dan panah adalah catatan sinyal pada candle tersebut, bukan rekomendasi entry yang masih aktif. Label entry setup aktif ditulis `BUY AKTIF` atau `SELL AKTIF`.

## Memperbarui ke versi 1.01

Lepaskan seluruh instance LiquidityReaper lama dari chart, ganti file `.ex5` di `MQL5/Indicators`, lalu pasang kembali satu instance. Nama indikator di daftar chart harus menunjukkan `v1.01`. Jika memakai dua instance dengan pengaturan berbeda, gunakan sudut dashboard berbeda agar tidak bertumpuk.

## Pengaturan dan perbedaan dari Pine

- `ClosedBarSignals=true`: hanya memproses candle selesai. Pada mode ini, pembaruan setup dan status SL/TP menunggu candle selesai.
- `ClosedBarSignals=false`: menghitung ulang candle berjalan; sinyal dan setup sementara dapat berubah/hilang sebelum close, seperti kalkulasi realtime Pine.
- `UseRealVolume=false`: menggunakan tick volume. Ubah ke true hanya jika broker/simbol menyediakan real volume. Jika real volume kosong, rasio kembali 1x sesuai fallback Pine; filter default 1.1x akan menolak sinyal.
- ATR menggunakan SMA sebagai seed lalu Wilder RMA, mengikuti ta.atr Pine.
- Urutan pemrosesan pool mengikuti Pine: pool terbaru diperiksa lebih dulu; jika banyak pool ditembus sekaligus, pending terakhir berasal dari pool tertua yang ditembus. Hanya satu pending per sisi; raid baru menggantikan pending sisi tersebut.
- Rail solid/dashed/dotted tersedia. Zona dan area risiko/reward menggunakan warna solid yang diredupkan karena objek chart MT5 tidak menampilkan transparansi seperti Pine.
- Dashboard tersedia pada empat sudut chart; ukuran teks memakai FontSize. Tidak meniru seluruh dekorasi dashboard Pine.
- ShowTargets hanya mengatur gambar; dashboard dan buffer setup tetap dihitung meskipun gambar dimatikan.
- TP harus berurutan: RRTP1 <= RRTP2 <= RRTP3. Status final target mengikuti TP tertinggi yang ditampilkan; jika semua TP dimatikan, hanya SL yang mengakhiri setup.
- DisplayHistoryBars=500 membatasi label/rail historis yang sudah tersapu. Seluruh data chart yang tersedia tetap dipakai untuk kalkulasi, sehingga riwayat sangat panjang atau mode live dapat lebih berat.
- Counter raids berdasarkan seluruh riwayat chart yang tersedia. Data broker, jumlah riwayat, dan volume dapat membuat hasil berbeda dari TradingView.
- PopupAlert, PushAlert, SoundAlert default mati. Push memerlukan konfigurasi Notifications MT5. Tidak mengirim alert historis saat pertama dipasang. Alert paling banyak sekali per waktu candle; pada mode live alert dapat berasal dari sinyal sementara.

## Buffer iCustom / Data Window

| Indeks | Isi |
|---|---|
| 0 | Harga panah BUY pada candle sinyal |
| 1 | Harga panah SELL pada candle sinyal |
| 2 | Entry pada candle setup baru |
| 3 | SL pada candle setup baru |
| 4 | TP1 pada candle setup baru |
| 5 | TP2 pada candle setup baru |
| 6 | TP3 pada candle setup baru |

Selain candle sinyal/setup, buffer berisi EMPTY_VALUE; level tidak diteruskan ke setiap candle. Dengan default closed-bar, baca shift 1 untuk candle terakhir yang selesai. ShowArrows=false menyembunyikan gambar tetapi buffer sinyal tetap tersedia.

## Validasi

Dikompilasi dengan MetaEditor MT5: 0 errors, 0 warnings, lihat LiquidityReaper.compile.log.
Belum diverifikasi visual pada chart MT5 atau dibandingkan bar per bar dengan TradingView menggunakan data OHLC/volume identik. Kompilasi tidak membuktikan kesetaraan seluruh sinyal atau kinerja trading.

Referensi implementasi MT5: https://www.mql5.com/en/docs/event_handlers/oncalculate dan https://www.mql5.com/en/docs/constants/objectconstants/enum_object/obj_trend.
