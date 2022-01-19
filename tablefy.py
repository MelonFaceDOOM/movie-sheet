def character_idx_closest_to_middle(p, s):
    '''Returns the position of the pattern p that is closest to the middle of the string s.'''
    middle = int(len(s)/2)
    closest_position = None
    closest_distance = len(s)
    for position in findall(p, s):
        distance_from_middle = abs(position-middle)
        if distance_from_middle < closest_distance:
            closest_distance = distance_from_middle
            closest_position = position
    return closest_position
    
def findall(p, s):
    '''Returns a list of all the positions of the pattern p in the string s.'''
    positions = []
    i = s.find(p)
    while i != -1:
        positions.append(i)
        i = s.find(p, i+1)
    return positions

class Tablefier:
    def __init__(self, data, max_table_width=None):
        if self.equal_columns_per_row(data):
            self.rows = self.data_to_rows(data)
        else:
            raise ValueError('Table requires inputted data to have an equal number of columns per row.')
        self.max_table_width = max_table_width
        self.n_columns = len(self.rows[0].cells)
        self.horizontal = '═'
        self.vertical = '║'
        self.topleft = '╔'
        self.topright = '╗'
        self.bottomleft = '╚'
        self.bottomright = '╝'
        self.rightjoint = '╠'
        self.leftjoint = '╣'
        self.upjoint = '╩'
        self.downjoint = '╦'
        self.fourjoint = '╬'
        
    def equal_columns_per_row(self, data):
        columns = len(data[0])
        for row in data:
            if len(row) != columns:
                return False
        return True
    
    def data_to_rows(self, data):
        rows = []
        for idx, row_data in enumerate(data):
            rows.append(Row(data=row_data, number=idx))
        return rows
    
    def column(self, col_index):
        the_column = []
        for row in self:
            the_column.append(row.cells[col_index])
        return the_column
    
    def column_width(self, col_index):
        column = self.column(col_index)
        return max([cell.width() for cell in column])
    
    def width(self):
        total_width = 0
        for i in range(self.n_columns):
            column = self.column(i)
            total_width += self.column_width(i)
        return total_width
    
    def widest_cell(self):
        max_width = 0
        current_widest_cell = None
        for row in self:
            widest_row_cell = row.widest_cell()
            if widest_row_cell.width() > max_width:
                max_width = widest_row_cell.width()
                current_widest_cell = widest_row_cell
        if not current_widest_cell:
            current_widest_cell = self.rows[0].cells[0]
        return current_widest_cell
    
    def shrink_to_max_width(self):
        border_character_width = self.n_columns + 1  # characters needed to draw border
        max_width = self.max_table_width - border_character_width
        if max_width < 2*self.n_columns:
            raise ValueError("max_width is too small")
        while True:
            widest_cell = self.widest_cell()
            column = self.column(widest_cell.col)
            widest_cell.shrink_widest_line()
            new_width = widest_cell.width()
            for cell in column:
                cell.shrink_lines_to_width(max_width=new_width)
            if self.width() <= max_width:
                break
                
    def draw(self):
        drawing = self.draw_top()
        for row in self.rows[:-1]:
            drawing += self.draw_row(row)
            drawing += self.draw_joining_line()
        drawing += self.draw_row(self.rows[-1])
        drawing += self.draw_bottom()
        return drawing
    
    def draw_row(self, row):
        row_output = ""
        line_idx = 0
        while True:
            line_cells = []
            for cell in row.cells:
                col_width = self.column_width(cell.col)
                try:
                    line_cell = cell.lines[line_idx]
                except IndexError:
                    line_cell = ""
                line_cells.append(line_cell)
            if not ("".join(line_cells)).replace(' ', ''):  # i.e. if all line cells are just empty or spaces
                break
            else:
                row_output += self.draw_nonjoining_line(line_cells)
                line_idx += 1
        return row_output
    
    def draw_line(self, leftcap, middlecap, rightcap):
        line = leftcap
        for col_idx in range(self.n_columns-1):
            col_width = self.column_width(col_idx)
            line += self.horizontal*col_width
            line += middlecap
        last_column_width = self.column_width(self.n_columns-1)
        line += self.horizontal*(last_column_width) + rightcap + '\n'
        return line   
    
    def draw_top(self):
        return self.draw_line(self.topleft, self.downjoint, self.topright)
    
    def draw_bottom(self):
        return self.draw_line(self.bottomleft, self.upjoint, self.bottomright)
    
    def draw_joining_line(self):
        return self.draw_line(self.rightjoint, self.fourjoint, self.leftjoint)
    
    def draw_nonjoining_line(self, contents):
        line = ""
        for i in range(self.n_columns):
            line += self.vertical
            content = contents[i]
            line += content
            col_width = self.column_width(i)
            extra_spaces = " "*(col_width - len(content))
            line += extra_spaces
        line += self.vertical + "\n"
        return line
    
    def __repr__(self):
        return "\n ".join([repr(row) for row in self])
    
    def __iter__(self):
        return iter(self.rows)
        
class Row:
    def __init__(self, data, number):
        self.cells = []
        self.number = number
        for idx, item in enumerate(data):
            self.cells.append(Cell(item, row=self.number, col=idx))
    
    def width(self):
        return sum([cell.width() for cell in self.cells])
    
    def widest_cell(self):
        index_max = max(range(len(self.cells)), key=self.cells.__getitem__)
        return(self.cells[index_max])
                
    def __repr__(self):
        return ", ".join([repr(cell) for cell in self])
    
    def __iter__(self):
        return iter(self.cells)

class Cell:
    def __init__(self, contents, row, col):
        self.lines = contents.split("/n")
        self.row = row
        self.col = col
        
    def width(self):
        return len(self.widest_line())
    
    def widest_line_idx(self):
        return max(enumerate(self.lines), key = lambda tup: len(tup[1]))[0]
    
    def widest_line(self):
        index_max = self.widest_line_idx()
        return(self.lines[index_max])
                    
    def replace_line_with_halves(self, line_idx):
        line = self.lines[line_idx]
        half_1, half_2 = split_string_by_space_or_half(line)
        del(self.lines[line_idx])
        self.lines.insert(line_idx, half_2)
        self.lines.insert(line_idx, half_1)
        
    def shrink_widest_line(self):
        widest_line_idx = self.widest_line_idx()
        self.replace_line_with_halves(widest_line_idx)

    def shrink_lines_to_width(self, max_width):
        any_lines_are_too_long = True
        while any_lines_are_too_long:
            for idx, line in enumerate(self.lines):
                if len(line) > max_width:
                    self.replace_line_with_halves(idx)
                    break
            else:
                any_lines_are_too_long = False

    def shrink_lines(self):
        # not used
        widest_line_idx = self.widest_line_idx()
        self.shrink_widest_line()
        new_width = max(self.lines[widest_line_idx], self.lines[widest_line_idx+1])
        self.shrink_lines_to_width(max_width=new_width)

    
    def __repr__(self):
        return " ".join(self.lines)
    
    def __iter__(self):
        return iter(self.lines)

    def __lt__(self, other):
        return self.width() < other.width()
    def __le__(self, other):
        return self.width() <= other.width()
    def __gt__(self, other):
        return self.width() > other.width()
    def __ge__(self, other):
        return self.width() >= other.width()
    def __eq__(self, other):
        return self.width() == other.width()
    def __ne__ (self, other):
        return self.width() != other.width()
        
def split_string_by_space_or_half(s):
    "split string s into line_1 and line_2. will use the closest space to the middle. If there is no space, it will split it in half"
    closest_space_to_middle = character_idx_closest_to_middle(" ", s)
    if closest_space_to_middle:
        half_1 = s[:closest_space_to_middle]
        half_2 = s[closest_space_to_middle + 1:]
    else:
        middle = int(len(s)/2)
        half_1 = s[:middle]
        half_2 = s[middle:]
    return half_1, half_2
