# assignment 1 IR 22k-4413
# importing necessary libraries
import os
import zipfile
import re
from nltk.stem import PorterStemmer
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from nltk.stem import PorterStemmer

# read stopwords from a file
def readStopwords(filePath):
    with open(filePath, 'r') as file:
        stopwords = set(line.strip() for line in file if line.strip())
    print("stopwords loaded successfully.")
    return stopwords

#this function performs tokenization using regex, converts text to lowercase, removes non-alphanumeric tokens,, removes stopwords, and applies stemming to reduce words to their root form (e.g., "running" to "run")
def preprocess(text, stopwords):
    tokens = re.findall(r'\b\w+\b', text)  # tokenization using regex (\b ensures word boundaries)
    tokens = [token.lower() for token in tokens]  # converting tokens to lowercase
    tokens = [token for token in tokens if token.isalnum() and token not in stopwords]  # removing stopwords and non-alphanumeric tokens
    stemmer = PorterStemmer()
    tokens = [stemmer.stem(token) for token in tokens]  # stemming using Porter Stemmer to normalize words
    return tokens

# building inverted and positional indexes
# inverted index: it maps each word to a set of document ids containing that word
# positional index: it stores the word positions in each document(useful for phrase and proximity searches)
def buildIndexes(abstracts, stopwords):
    invertedIndex = {}
    positionalIndex = {}
    for docId, text in abstracts.items():
        tokens = preprocess(text, stopwords)
        for pos, token in enumerate(tokens):
            # updating inverted index
            if token not in invertedIndex:
                invertedIndex[token] = set()
            invertedIndex[token].add(docId)

            # updating positional index
            if token not in positionalIndex:
                positionalIndex[token] = {}
            if docId not in positionalIndex[token]:
                positionalIndex[token][docId] = []
            positionalIndex[token][docId].append(pos)
    print("indexes built successfully.")
    return invertedIndex, positionalIndex

# evaluating boolean queries using AND, OR, and NOT operations
def evaluateQuery(query, invertedIndex):
    terms = query.split()
    operators = []
    result = None
    for i, term in enumerate(terms):
        # check if the term is a logical operator (AND, OR, NOT)
        if term.upper() in ["AND", "OR", "NOT"]:
            operators.append(term.upper())
        else:
            term = preprocess(term, stopwords)[0]
            if term not in invertedIndex:
                termDocs = set()
            else:
                termDocs = invertedIndex[term]
            # apply NOT operator (if applicable)
            if i > 0 and terms[i - 1].upper() == "NOT":
                termDocs = set(invertedIndex.keys()) - termDocs
            # apply AND and OR operators based on user input
            if result is None:
                result = termDocs
            else:
                if operators:
                    operator = operators[-1]
                    if operator == "AND":
                        result = result.intersection(termDocs)
                    elif operator == "OR":
                        result = result.union(termDocs)
    return result

#evaluating proximity query
def evaluateProximityQuery(query, positionalIndex, stopwords):
    stemmer = PorterStemmer()
    # match the pattern 'term1 term2 /k'
    match = re.match(r'(.+?)\s+(.+?)\s*/(\d+)', query)
    if not match:
        print("Invalid query format. Use 'term1 term2 /k'")
        return set()
    term1, term2, k = match.groups()
    k = int(k)
    # preprocess and stem terms
    term1_tokens = preprocess(term1, stopwords)
    term2_tokens = preprocess(term2, stopwords)
    if not term1_tokens or not term2_tokens:
        print("Error processing terms.")
        return set()
    # stem all tokens to consider word variations
    term1_stems = {stemmer.stem(token) for token in term1_tokens}
    term2_stems = {stemmer.stem(token) for token in term2_tokens} 
    # print(f"Processed terms: term1='{term1_stems}', term2='{term2_stems}', k={k}")
    # find matching documents for all stemmed variations
    docsWithTerm1 = set()
    docsWithTerm2 = set()
    for stem in term1_stems:
        if stem in positionalIndex:
            docsWithTerm1.update(doc for doc, positions in positionalIndex[stem].items() if len(positions) >= k)
    for stem in term2_stems:
        if stem in positionalIndex:
            docsWithTerm2.update(doc for doc, positions in positionalIndex[stem].items() if len(positions) >= k)
    resultDocs = docsWithTerm1.intersection(docsWithTerm2)
    # print(f"Result documents: {resultDocs}")
    return resultDocs

# loadAbstract loads abstracts from a zip file using multiple encodings some files are encoded in different character sets, so multiple encodings are tried ['latin-1', 'ISO-8859-1', 'Windows-1252'] are common encodings for text files
def loadAbstracts(zipFile):
    abstracts = {}
    with zipfile.ZipFile(zipFile, 'r') as zipRef:
        for fileName in zipRef.namelist():
            with zipRef.open(fileName) as file:
                docId = os.path.splitext(os.path.basename(fileName))[0]
                try:
                    abstracts[docId] = file.read().decode('utf-8')
                except UnicodeDecodeError:
                    fileContent = file.read()
                    for encoding in ['latin-1', 'ISO-8859-1', 'Windows-1252']:
                        try:
                            abstracts[docId] = fileContent.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        print(f"Warning: Could not decode file {fileName} with any supported encoding.")
                        abstracts[docId] = ""
    return abstracts

# indexes saved using JSON (easy to read and write)
def saveIndexes(invertedIndex, positionalIndex):
    with open('inverted_indexes.json', 'w') as f:
        json.dump({k: list(v) for k, v in invertedIndex.items()}, f)
    with open('positional_indexes.json', 'w') as f:
        json.dump(positionalIndex, f)
    print("Indexes saved to files.")

# load indexes from files
def loadIndexes():
    with open('inverted_indexes.json', 'r') as f:
        invertedIndex = {k: set(v) for k, v in json.load(f).items()}
    with open('positional_indexes.json', 'r') as f:
        positionalIndex = json.load(f)
    print("indexes loaded from files.")
    return invertedIndex, positionalIndex

# function to handle query submission
def submitQuery():
    query = queryEntry.get().strip()
    if not query:
        messagebox.showerror("Error", "Enter a query!!!")
        return
    if "/" in query:
        results = evaluateProximityQuery(query, positionalIndex, stopwords)
    else:
        results = evaluateQuery(query, invertedIndex)
    if results:
        sortedResults = sorted(results, key=lambda x: int(re.search(r'\d+', x).group()))
        resultText.config(state=tk.NORMAL)
        resultText.delete(1.0, tk.END)
        resultText.insert(tk.END, f"results: {', '.join(sortedResults)}")
        resultText.config(state=tk.DISABLED)
    else:
        resultText.config(state=tk.NORMAL)
        resultText.delete(1.0, tk.END)
        resultText.insert(tk.END, "no results found.")
        resultText.config(state=tk.DISABLED)

# initialize the main application for GUI
def initializeApp():
    global stopwords, invertedIndex, positionalIndex
    with open("Stopword-List.txt", 'r') as file:
        stopwords = set(line.strip() for line in file if line.strip())
    print("stopwords loaded successfully.")
    abstracts = loadAbstracts('Abstracts.zip')
    invertedIndex, positionalIndex = buildIndexes(abstracts, stopwords)
    saveIndexes(invertedIndex, positionalIndex)
    invertedIndex, positionalIndex = loadIndexes()

# main window IS CREATED
root = ttk.Window(themename="cosmo")
root.title("Boolean Retrieval")
root.geometry("1600x1200")

# frame for the search bar and buttons
searchFrame = ttk.Frame(root)
searchFrame.pack(pady=20)

#enter query label
queryLabel = ttk.Label(searchFrame, text="Input query:")
queryLabel.pack(side=tk.LEFT, padx=10)

#search entry
queryEntry = ttk.Entry(searchFrame, width=50)
queryEntry.pack(side=tk.LEFT, padx=10)

#submit button
submitButton = ttk.Button(searchFrame, text="search", command=submitQuery, bootstyle=PRIMARY)
submitButton.pack(side=tk.LEFT)

#results text area
resultText = scrolledtext.ScrolledText(root, width=90, height=20, state=tk.DISABLED)
resultText.pack(pady=20)

initializeApp()
root.mainloop()
