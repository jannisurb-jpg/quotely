import torch
import torch.nn as nn
import torch.nn.functional as F
import pickle

# Kategorien
categories = ["Sport", "Freizeit", "Arbeit", "Motivation", "Sonstiges", "Emotionen", "News/Politik", "Technik", "Humor"]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Vectorizer laden
with open("vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)

input_size = len(vectorizer.get_feature_names_out())
hidden_size = 128
output_size = len(categories)

# Modell
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.dropout = nn.Dropout(p=0.2)

    def forward(self, X):
        X = torch.relu(self.fc1(X))
        X = self.dropout(X)
        X = torch.relu(self.fc2(X))
        X = self.dropout(X)
        X = self.fc3(X)
        return F.log_softmax(X, dim=1)

# Modell laden
model = Net()
model.load_state_dict(torch.load("multi_class_model.pth", map_location=device))
model.to(device)
model.eval()


def CategorizePost(content):

    sample_vec = vectorizer.transform([content]).toarray()
    sample_tensor = torch.from_numpy(sample_vec).float().to(device)

    with torch.no_grad():
        output = model(sample_tensor)
        probs = torch.exp(output)

    probs_list = probs.tolist()[0]

    return probs_list