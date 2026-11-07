# Proyek Analisis Data: E-Commerce Public Dataset (Olist)

Analisis data pesanan marketplace Olist (Brasil) periode **Januari 2017 – Agustus 2018**, mencakup kategori produk,
tren bulanan, dampak keterlambatan pengiriman terhadap review, serta segmentasi pelanggan (RFM) dan analisis geospasial.
Hasil analisis disajikan dalam `notebook.ipynb` dan dashboard interaktif Streamlit.

Sumber data: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

## Pertanyaan Bisnis
1. Kategori produk apa saja yang menjadi 10 penyumbang revenue tertinggi dan terendah, dan berapa kontribusi 10 teratas?
2. Bagaimana tren jumlah pesanan dan revenue bulanan (MoM) dan kapan puncaknya?
3. Berapa selisih review score antara pesanan terlambat dan tepat waktu, dan state mana yang paling sering terlambat?
4. Bagaimana sebaran pelanggan menurut segmen RFM dan segmen mana yang menyumbang revenue terbesar?

## Struktur Direktori
```
submission
├───dashboard
│   ├───main_data.csv      # data bersih tingkat item pesanan (hasil notebook)
│   └───dashboard.py       # aplikasi Streamlit
├───data                   # dataset asli
├───notebook.ipynb         # proses analisis lengkap
├───README.md
├───requirements.txt
└───url.txt                # tautan dashboard di Streamlit Cloud
```

## Setup Environment
Disarankan Python 3.10 atau lebih baru.

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Menjalankan Dashboard
Jalankan dari **folder utama proyek** (folder yang berisi `README.md`):

```
streamlit run dashboard/dashboard.py
```

Dashboard terbuka di `http://localhost:8501`. Gunakan filter di sidebar (rentang tanggal, state, jumlah kategori, minimum
pesanan per state) untuk mengeksplorasi data.

## Menjalankan Ulang Notebook
Notebook membaca berkas dari folder `data/` (jalankan dari folder utama proyek) dan menulis ulang `dashboard/main_data.csv`.
Untuk membukanya dibutuhkan Jupyter, misalnya `pip install notebook` lalu `jupyter notebook notebook.ipynb`.

## Deploy ke Streamlit Cloud
1. Unggah folder proyek ke repositori GitHub (pastikan `dashboard/main_data.csv` dan `requirements.txt` ikut).
2. Di [share.streamlit.io](https://share.streamlit.io), pilih *New app* lalu arahkan ke repositori tersebut.
3. Isi *Main file path* dengan `dashboard/dashboard.py`, lalu deploy.
4. Salin tautan aplikasi ke `url.txt`.

## Teknik Analisis Lanjutan
- **RFM Analysis** dengan binning berbasis aturan bisnis (6 segmen pelanggan).
- **Geospatial Analysis**: peta gelembung per state (ukuran = jumlah pesanan, warna = % pesanan terlambat).
- **Binning / manual grouping**: kelompok keterlambatan pengiriman dan tingkat recency/monetary.
