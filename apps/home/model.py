import torch
import torch.nn as nn
from apps.home.nltk_utils import tokenize, bag_of_words, expand_expressions, get_synonyms_bert


class NeuralNet(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(NeuralNet, self).__init__()
        self.l1 = nn.Linear(input_size, hidden_size)
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.relu = nn.LeakyReLU(0.1)
        self.dropout = nn.Dropout(0.3)
        self.l2 = nn.Linear(hidden_size, hidden_size)
        self.bn2 = nn.BatchNorm1d(hidden_size)
        self.l3 = nn.Linear(hidden_size, output_size)
        self.attention = nn.MultiheadAttention(hidden_size, num_heads=16)
        self.weights_init()  # Initialisation des poids

    def forward(self, x):
        out = self.l1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.l2(out)
        out = self.bn2(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.l3(out)
        return out

    def attention_weights(self, x):
        x = x.permute(1, 0, 2)  # Permutation pour la compatibilité de la forme
        weights, _ = self.attention(x, x, x)
        # Utilisation de log-softmax
        weights = torch.log_softmax(weights, dim=1)
        return weights

    def weights_init(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight.data)
                nn.init.zeros_(module.bias.data)

    def predict(self, sentence, all_words, tags, lang):
        tokens = tokenize(sentence, lang)
        expanded_tokens = expand_expressions(tokens, lang)
        # Appel à la fonction get_synonyms
        synonyms = get_synonyms_bert(expanded_tokens, lang)
        expanded_tokens.extend(synonyms)

        X = bag_of_words(expanded_tokens, all_words, lang)
        X = torch.from_numpy(X).to(torch.float32).unsqueeze(0)
        output = self(X)

        attention_weights = self.attention_weights(output)
        attention_output = torch.matmul(
            attention_weights.transpose(1, 2), output)
        aggregated_output = torch.mean(attention_output, dim=1)

        _, predicted = torch.max(aggregated_output, dim=1)
        tag = tags[predicted.item()]
        probs = torch.softmax(aggregated_output, dim=1)
        prob = probs[0][predicted.item()].item()

        return tag, prob
