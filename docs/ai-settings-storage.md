# Penyimpanan pengaturan AI

Pengaturan AI kini disimpan permanen di `data/ai-settings.dpapi`, terpisah dari SQLite log trading. Seluruh isi (API key, platform, URL, model) dienkripsi menggunakan Windows DPAPI untuk akun Windows yang menjalankan server. Tidak ada dependensi tambahan.

Simpan konfigurasi melalui Pengaturan sekali untuk membuat berkas terenkripsi. Setelah restart, server memuatnya kembali otomatis. Kolom API key tetap kosong di browser; kosongkan saat mengubah model untuk mempertahankan key. Hapus key server menyimpan nilai kosong secara permanen, termasuk menonaktifkan fallback key environment untuk konfigurasi tersebut.

Berkas ini tercakup pengecualian Git `data/`. Cadangkan secara terpisah dari SQLite jika diperlukan. Pemindahan ke akun Windows/komputer lain memerlukan pengisian key ulang. Jika dekripsi gagal, Pengaturan menampilkan pesan agar konfigurasi disimpan ulang. Penyimpanan dilakukan atomik; kegagalan tulis tidak mengganti konfigurasi aktif.

Uji: `python -m unittest test_ai_notes -v`.
