class Substrings:
    def __init__(self, term):
        self.name = term.lower()
        self.substrings = self.get_substrings()
        # TODO: test this change
        if self.substrings:
            self.max = max(self.substrings.keys())
        else:
            self.max = 0
    
    def get_substrings(self):
        substrings = {}
        frame_length = 1
        while frame_length <= len(self.name):
            n_frames = len(self.name) - frame_length + 1
            frame_substrings = []
            for i in range(n_frames):
                frame_substrings.append(self.name[i:i+frame_length])
            substrings[frame_length] = frame_substrings
            frame_length += 1
        return substrings
    
    def best_match(self, comparator):
        best_match = ""
        length = self.max + 1
        while length:
            length -= 1
            try:
                 comparator_substrings = comparator.substrings[length]
            except KeyError:
                continue

            for substring in comparator_substrings:
                if substring in self.substrings[length]:
                    match = substring
                    return match
        return None


def find_closest_match(term, bank, threshold=50):
    substr_match = ""
    full_match = ""
    term_substrings = Substrings(term)
    for word in bank:
        word_substrings = Substrings(word)
        match = term_substrings.best_match(word_substrings)
        if match:
            if len(match) > len(substr_match):
                substr_match = match
                full_match = word
            if len(match) == len(substr_match):
                substr_match = match
                full_match = word if len(word)<len(full_match) else full_match
    if len(substr_match) < (len(term)*threshold/100):
        return None
    return full_match