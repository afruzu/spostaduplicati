import os
import hashlib
import csv
import shutil
from collections import defaultdict
from tkinter import Tk, filedialog, messagebox, Toplevel, Label, Button
from tkinter.ttk import Progressbar
from PIL import Image
from pathlib import Path
import webbrowser
import base64
from io import BytesIO

# === Estensioni multimediali supportate ===
ESTENSIONI = {
    'immagini': ('.jpg', '.jpeg', '.png', '.bmp', '.gif'),
    'video': ('.mp4', '.mov', '.avi', '.mkv'),
    'audio': ('.mp3', '.wav', '.aac', '.flac'),
    'documenti': ('.pdf', '.doc', '.docx', '.txt', '.xlsx'),
    'compressi': ('.zip', '.7z')
}
TUTTE_ESTENSIONI = ESTENSIONI['immagini'] + ESTENSIONI['video'] + ESTENSIONI['audio'] + ESTENSIONI['documenti'] + ESTENSIONI['compressi'] 
def calcola_md5(percorso_file):
    hash_md5 = hashlib.md5()
    with open(percorso_file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def calcola_sha256(percorso_file):
    hash_sha = hashlib.sha256()
    with open(percorso_file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha.update(chunk)
    return hash_sha.hexdigest()

def trova_duplicati(cartella):
    preliminari = defaultdict(list)
    tutti_file = []
    for root, _, files in os.walk(cartella):
        for nome_file in files:
            if nome_file.lower().endswith(TUTTE_ESTENSIONI):
                tutti_file.append(os.path.join(root, nome_file))

    finestra = Toplevel()
    finestra.title("Analisi duplicati in corso")
    Label(finestra, text="Sto analizzando i file...").pack(pady=10)
    barra = Progressbar(finestra, length=300, mode='determinate', maximum=len(tutti_file))
    barra.pack(pady=10)
    finestra.update()

    for i, percorso in enumerate(tutti_file):
        try:
            dimensione = os.path.getsize(percorso)
            md5 = calcola_md5(percorso)
            chiave = (dimensione, md5)
            preliminari[chiave].append(percorso)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore con {os.path.basename(percorso)}: {e}")
        barra['value'] = i + 1
        finestra.update()

    finestra.destroy()

    duplicati_finali = {}
    for (dim, md5), file_list in preliminari.items():
        if len(file_list) > 1:
            sha_groups = defaultdict(list)
            for percorso in file_list:
                sha256 = calcola_sha256(percorso)
                chiave_finale = (dim, md5, sha256)
                sha_groups[chiave_finale].append(percorso)
            for k, v in sha_groups.items():
                if len(v) > 1:
                    duplicati_finali[k] = v
    return duplicati_finali

def esporta_csv(risultati, nome_file_csv="duplicati.csv"):
    finestra = Toplevel()
    finestra.title("Creazione CSV in corso")
    Label(finestra, text="Sto creando il file CSV...").pack(pady=10)
    barra = Progressbar(finestra, length=300, mode='determinate', maximum=len(risultati))
    barra.pack(pady=10)
    finestra.update()

    with open(nome_file_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_NONE, escapechar='\\')
        if not risultati:
            messagebox.showwarning("Nessun risultato", "Non ci sono dati da esportare nel CSV.")
            return

        max_copie = max(len(v) for v in risultati.values())
        intestazione = ["Dimensione", "MD5", "SHA-256", "Tipo"] + [f"File {i+1}" for i in range(max_copie)]
        writer.writerow(intestazione)

        for i, ((dim, md5, sha256), files) in enumerate(risultati.items()):
            estensione = os.path.splitext(files[0])[1].lower()
            riga = [str(dim), md5, sha256, estensione] + [os.path.basename(f) for f in files]
            riga += [""] * (max_copie - len(files))
            writer.writerow(riga)
            barra['value'] = i + 1
            finestra.update()

    finestra.destroy()
    return True


def trova_file(nome_file, cartella):
    for root, _, files in os.walk(cartella):
        if nome_file in files:
            return os.path.join(root, nome_file)
    return None

def crea_thumbnail_base64(img_path):
    """Crea una thumbnail dell'immagine e la restituisce in formato Base64."""
    try:
        with Image.open(img_path) as img:
            img.thumbnail((150, 150))
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Errore nella creazione della thumbnail per {img_path}: {e}")
        return None

def genera_report_html(gruppi, apri_automaticamente, html_path):
    # Finestra di avanzamento
    finestra = Toplevel()
    finestra.title("Generazione report HTML")
    Label(finestra, text="Sto generando il report visivo...").pack(pady=10)
    barra = Progressbar(finestra, length=300, mode='determinate', maximum=len(gruppi))
    barra.pack(pady=10)
    finestra.update()

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Duplicati Visivi</title></head><body>")
        f.write("<h1>Report Interattivo dei Duplicati Multimediali</h1>")
        for i, gruppo in enumerate(gruppi, 1):
            f.write(f"<h2>Gruppo {i}</h2><div style='display:flex; gap:20px; flex-wrap:wrap;'>")
            for file_path in gruppo:
                est = os.path.splitext(file_path)[1].lower()
                nome = os.path.basename(file_path)
                try:
                    if est in ESTENSIONI['immagini']:
                        base64_img = crea_thumbnail_base64(file_path)
                        if base64_img:
                            f.write(f"<div><img src='{base64_img}' style='max-height:150px;'><br>{nome}</div>")
                        else:
                            f.write(f"<div>Errore con {nome}</div>")
                    elif est in ESTENSIONI['video']:
                        f.write(f"<div><video controls width='200'><source src='{file_path}' type='video/{est[1:]}'></video><br>{nome}</div>")
                    elif est in ESTENSIONI['audio']:
                        f.write(f"<div><audio controls><source src='{file_path}' type='audio/{est[1:]}'></audio><br>{nome}</div>")
                    else:
                        f.write(f"<div><a href='{file_path}' target='_blank'>{nome}</a></div>")
                except Exception as e:
                    f.write(f"<div>Errore con {nome}</div>")
            f.write("</div><hr>")
            barra['value'] = i
            finestra.update()

        f.write("</body></html>")

    finestra.destroy()

    # Rimuove la cartella 'thumbnails' se esiste, dato che non è più necessaria.
    thumb_dir = Path("thumbnails")
    if thumb_dir.exists():
        try:
            shutil.rmtree(thumb_dir)
        except OSError as e:
            messagebox.showwarning("Pulizia fallita", f"Errore: {e.filename} - {e.strerror}.")


    if apri_automaticamente:
        webbrowser.open_new_tab(os.path.abspath(html_path))

def gestisci_duplicati(file_csv, cartella_analisi, cartella_destinazione):
    duplicati = []
    spostati = 0
    with open(file_csv, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)
        righe = list(reader)

    finestra = Toplevel()
    finestra.title("Spostamento duplicati")
    Label(finestra, text="Sto spostando i file duplicati...").pack(pady=10)
    barra = Progressbar(finestra, length=300, mode='determinate', maximum=len(righe))
    barra.pack(pady=10)
    finestra.update()

    for i, riga in enumerate(righe):
        files = riga[4:]
        files = [f for f in files if f.strip()]
        if len(files) < 2:
            barra['value'] = i + 1
            finestra.update()
            continue

        gruppo = []
        for j, nome_file in enumerate(files):
            percorso = trova_file(nome_file, cartella_analisi)
            if not percorso:
                messagebox.showwarning("File non trovato", f"{nome_file} non è stato trovato nella cartella di origine.")
                continue
            if j == 0:
                gruppo.append(percorso)
            else:
                destinazione = os.path.join(cartella_destinazione, os.path.basename(percorso))
                try:
                    shutil.move(percorso, destinazione)
                    spostati += 1
                    gruppo.append(destinazione)
                except Exception as e:
                    messagebox.showerror("Errore di spostamento", f"Errore nello spostamento di {nome_file}: {e}")
        if len(gruppo) > 1:
            duplicati.append(gruppo)

        barra['value'] = i + 1
        finestra.update()

    finestra.destroy()
    
    risposta = messagebox.askyesno("Spostamento completato", f"Sono stati spostati con successo {spostati} file duplicati.\n\nVuoi aprire il report visivo dei duplicati?")
    return duplicati, risposta


def finestra_info(testo, titolo="Informazione", larghezza=700, altezza=600):
    win = Toplevel()
    win.title(titolo)
    win.resizable(False, False)

    # Calcolo posizione centrale
    x = (win.winfo_screenwidth() // 2) - (larghezza // 2)
    y = (win.winfo_screenheight() // 2) - (altezza // 2)
    win.geometry(f"{larghezza}x{altezza}+{x}+{y}")

    # Etichetta con testo
    label = Label(
        win,
        text=testo,
        font=("Helvetica", 13),
        wraplength=larghezza - 40,
        justify="left",
        anchor="nw"
    )
    label.pack(pady=20, padx=20, fill="both", expand=True)

    # Pulsante OK
    Button(win, text="OK", command=win.destroy, font=("Helvetica", 11)).pack(pady=10)

    win.grab_set()
    win.wait_window()


# === Esecuzione principale ===

Tk().withdraw()

finestra_info("Questo programma analizza file multimediali, documenti in pdf e di word/excel e files compressi contenuti in una cartella a scelta (immagini, video, audio, documenti, compressi), identifica duplicati, "
    "genera un file CSV esaminabile per controllo in Excel, sposta i duplicati in un'altra cartella sempre a tua scelta e crea un report HTML interattivo che ti permetterà di vedere i files duplicati spostati.\n\n"
    "Ti verrà chiesto di selezionare:\n"
    "1. La cartella da analizzare\n"
    "2. La cartella di destinazione per i duplicati\n"
    "\n"
    "\n"
    "Il processo è piuttosto lungo se ci sono molti files, ti ricordo di ASPETTARE il riquadro che segnala la fine del processo oltre che di confermare i passaggi intermedi quando richiesto.\n"
    "\n"
    "NIENTE VIENE CANCELLATO O RIMOSSO, SOLTANTO SPOSTATO. SPERO CHE QUESTA APPLICAZIONE TI SIA UTILE - Afruzu\n", "BENVENUTO IN SPOSTADUPLICATIMULTIMEDIALI",
    larghezza=600, altezza=480)

cartella_analisi = filedialog.askdirectory(title="Seleziona la cartella da analizzare")
if not cartella_analisi:
    messagebox.showwarning("Operazione annullata", "Nessuna cartella selezionata. Il programma verrà chiuso.")
    exit()

risultati = trova_duplicati(cartella_analisi)
if not risultati:
    messagebox.showinfo("Nessun duplicato", "Non sono stati trovati duplicati nella cartella selezionata.")
    exit()

cartella_destinazione = filedialog.askdirectory(title="Seleziona la cartella di destinazione per i duplicati")
if not cartella_destinazione:
    messagebox.showwarning("Operazione annullata", "Nessuna cartella di destinazione selezionata. Il programma verrà chiuso.")
    exit()

percorso_csv = os.path.join(cartella_destinazione, "duplicati.csv")
esporta_csv(risultati, percorso_csv)

messagebox.showinfo("CSV creato", f"Il file 'duplicati.csv' è stato creato correttamente in:\n\n{percorso_csv}")

gruppi, risposta = gestisci_duplicati(percorso_csv, cartella_analisi, cartella_destinazione)

percorso_html = os.path.join(cartella_destinazione, "report_duplicati.html")
genera_report_html(gruppi, apri_automaticamente=risposta, html_path=percorso_html)

finestra_info("✅ Il processo è terminato con successo.\n\nSono stati generati:\n"
    f"- Il file 'duplicati.csv' in:\n{percorso_csv}\n\n"
    f"- Il file 'report_duplicati.html' in:\n{percorso_html}\n\n"
    "Puoi consultare il report HTML per un confronto visivo e interattivo dei duplicati.\n"
    "\n"
    "Tutti i files generati sono nella cartella in cui sono stati spostati i duplicati", "OPERAZIONE COMPLETATA",
    larghezza=600, altezza=400)
