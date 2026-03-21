import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

import torch
import torch.nn as nn
from torch.nn import functional as F

# ── Setup ─────────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
categories = ["Sport", 
              "Freizeit",
              "Arbeexit/Schule",
              "Motivation",
              "Emotionen/Gefühle",
              "News/Politik", 
              "Technik", 
              "Humor"]

# ── Daten laden ───────────────────────────────────────────────
dataset = pd.read_csv('QuotesNEw.txt', delimiter='\t', header=None, quoting=3, encoding='utf-8')
dataset = dataset[dataset[1].notna()]
dataset[1] = dataset[1].astype(int)
print("Einzigartige Labels:", dataset[1].unique())
print("Samples pro Kategorie:")
for i, cat in enumerate(categories):
    print(f"  {cat:22} {(dataset[1] == i).sum()}x")

# ── Embedder ──────────────────────────────────────────────────
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

print("\nErstelle Embeddings...")
raw_texts = dataset.iloc[:, 0].astype(str).tolist()
X = embedder.encode(raw_texts, show_progress_bar=True, batch_size=64)
y = dataset.iloc[:, 1].values

# ── Train-Test-Split ──────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
print(f"Train: {X_train.shape[0]} | Test: {X_test.shape[0]}")

Xtrain_ = torch.from_numpy(X_train).float().to(device)
Xtest_  = torch.from_numpy(X_test).float().to(device)
ytrain_ = torch.from_numpy(y_train).long().to(device)
ytest_  = torch.from_numpy(y_test).long().to(device)

# ── Modell ────────────────────────────────────────────────────
input_size  = X.shape[1]  # 384
output_size = len(categories)

class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.fc1     = nn.Linear(input_size, 256)
        self.bn1     = nn.BatchNorm1d(256)
        self.fc2     = nn.Linear(256, 128)
        self.bn2     = nn.BatchNorm1d(128)
        self.fc3     = nn.Linear(128, 64)
        self.fc4     = nn.Linear(64, output_size)
        self.dropout = nn.Dropout(p=0.3)

    def forward(self, X):
        X = self.dropout(torch.relu(self.bn1(self.fc1(X))))
        X = self.dropout(torch.relu(self.bn2(self.fc2(X))))
        X = torch.relu(self.fc3(X))
        return F.log_softmax(self.fc4(X), dim=1)

model = Net().to(device)

# ── Training ──────────────────────────────────────────────────
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
loss_fn   = nn.NLLLoss()
epochs    = 100

print("\nTraining startet...\n")
for epoch in range(epochs):
    model.train()
    optimizer.zero_grad()
    loss = loss_fn(model(Xtrain_), ytrain_)
    loss.backward()
    optimizer.step()

    if (epoch + 1) % 10 == 0:
        model.eval()
        with torch.no_grad():
            val_loss = loss_fn(model(Xtest_), ytest_)
            val_acc  = (torch.argmax(model(Xtest_), dim=1) == ytest_).float().mean()
        print(f"Epoch {epoch+1:3d}/{epochs} | Train: {loss.item():.4f} | Val: {val_loss.item():.4f} | Acc: {val_acc:.2%}")

torch.save(model.state_dict(), "multi_class_model.pth")
print("\nModell gespeichert!")

# ── Aktives Lernen ────────────────────────────────────────────
pending_examples   = []
RETRAIN_THRESHOLD  = 3

def save_new_example(text, label):
    with open("QuotesNEw.txt", "a", encoding="utf-8") as f:
        f.write(f"{text}\t{label}\n")

def retrain():
    global pending_examples, X_train, y_train

    print(f"\nNachtraining mit {len(pending_examples)} neuen Beispielen...")

    for vec, label in pending_examples:
        X_train = np.vstack([X_train, vec])
        y_train = np.append(y_train, label)

    # Mix aus alten + neuen damit Modell nichts vergisst
    sample_size = min(1000, len(X_train))
    indices     = np.random.choice(len(X_train), sample_size, replace=False)

    Xt = torch.from_numpy(X_train[indices]).float().to(device)
    yt = torch.from_numpy(y_train[indices]).long().to(device)

    retrain_optimizer = torch.optim.Adam(model.parameters(), lr=0.00005)
    retrain_loss_fn   = nn.NLLLoss()

    model.train()
    for _ in range(50):
        retrain_optimizer.zero_grad()
        loss = retrain_loss_fn(model(Xt), yt)
        loss.backward()
        retrain_optimizer.step()

    model.eval()
    pending_examples.clear()
    torch.save(model.state_dict(), "multi_class_model.pth")
    print("Nachtraining fertig, Modell gespeichert!\n")

# ── Hilfsfunktion ─────────────────────────────────────────────
def text_to_tensor(text):
    vec = embedder.encode([text])
    return torch.from_numpy(vec).float().to(device), vec

# ── CategorizePost (für dein Social Media System) ─────────────
def CategorizePost(content):
    """
    content       = der Text des Posts
    correct_label = falls bekannt die richtige Kategorie (0-7)
                    z.B. wenn User likt → Label des Posts mitgeben
                    None = KI entscheidet alleine
    
    Gibt Liste mit 8 Wahrscheinlichkeiten zurück.
    """
    model.eval()
    tensor, vec = text_to_tensor(content)

    with torch.no_grad():
        probs      = torch.exp(model(tensor))[0]
        pred_label = torch.argmax(probs).item()
        confidence = probs[pred_label].item()

    # Aktives Lernen: war die KI falsch?
    pending_examples.append((vec, pred_label))
    save_new_example(content, pred_label)
    print(f"[Lernfortschritt] {len(pending_examples)}/{RETRAIN_THRESHOLD} Korrekturen gesammelt")

    if len(pending_examples) >= RETRAIN_THRESHOLD:
        retrain()

    return probs.tolist()

# ── Interaktive Eingabe ───────────────────────────────────────
def AskForInput():
    CONFIDENCE_THRESHOLD = 0.65
    model.eval()

    while True:
        text = input("\nText eingeben (exit zum Beenden): ")
        if text.lower() in ["exit", "quit"]:
            print("Programm beendet.")
            break

        tensor, vec = text_to_tensor(text)

        with torch.no_grad():
            probs      = torch.exp(model(tensor))[0]
            pred_label = torch.argmax(probs).item()
            confidence = probs[pred_label].item()

        print(f"\nVorhersage: {categories[pred_label]} ({confidence:.0%})")
        print("Wahrscheinlichkeiten:")
        for i, cat in enumerate(categories):
            bar = "█" * int(probs[i].item() * 20)
            print(f"  {cat:22} {probs[i].item():.0%}  {bar}")

        # Zu unsicher → User fragen
        if confidence < CONFIDENCE_THRESHOLD:
            print("\nUnsicher! Richtige Kategorie eingeben (Enter = KI hat recht):")
            for i, cat in enumerate(categories):
                print(f"  {i} = {cat}")

            user_input = input("Deine Eingabe: ").strip()

            if user_input == "":
                pending_examples.append((vec, pred_label))
                save_new_example(text, pred_label)
                print("Bestätigt!")

            elif user_input.isdigit() and 0 <= int(user_input) < len(categories):
                correct = int(user_input)
                pending_examples.append((vec, correct))
                save_new_example(text, correct)
                print(f"Gespeichert als: {categories[correct]}")
                print(f"[Lernfortschritt] {len(pending_examples)}/{RETRAIN_THRESHOLD}")

                if len(pending_examples) >= RETRAIN_THRESHOLD:
                    retrain()

AskForInput()