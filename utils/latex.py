import re

class LatexTable:
    """Chainable LaTeX table transformer. Use: LatexTable(df.to_latex()).remove_separators().set_small_font()..."""

    def __init__(self, latex_str: str):
        self._latex = latex_str

    def __str__(self):
        return self._latex

    def remove_separators(self):
        """Remove \\hline, \\toprule, \\midrule, \\bottomrule."""
        self._latex = (self._latex
                       .replace('\\hline', '')
                       .replace('\\toprule', '')
                       .replace('\\midrule', '')
                       .replace('\\bottomrule', ''))
        return self

    def set_small_font(self, size: str = r'\small', colsep: int = 3):
        """Insert font size and \\tabcolsep before \\begin{tabular}."""
        self._latex = self._latex.replace(
            r'\begin{tabular}',
            f'{size}\\setlength{{\\tabcolsep}}{{{colsep}pt}}\\begin{{tabular}}'
        )
        return self

    def bold_headers(self):
        """Bold the first line of content inside the tabular (the header row)."""
        lines = self._latex.split('\n')
        in_tabular = False
        for i, line in enumerate(lines):
            if r'\begin{tabular}' in line:
                in_tabular = True
                continue
            if in_tabular and line.strip() and not line.strip().startswith('%'):
                cells = line.split('&')
                new_cells = []
                for cell in cells:
                    if cell.strip().endswith('\\\\'):
                        content = cell.strip()[:-2].strip()
                        new_cell = f'\\textbf{{{content}}} \\\\'
                    else:
                        content = cell.strip()
                        new_cell = f'\\textbf{{{content}}}'
                    new_cells.append(new_cell)
                new_line = ' & '.join(new_cells)
                lines[i] = new_line
                break
        self._latex = '\n'.join(lines)
        return self

    def fit_to_width(self):
        """Replace tabular with tabular*{\\textwidth} and add \\extracolsep{\\fill}."""
        pattern = r'(\\begin\{tabular\})(\*?)(\{[^}]+\})(.*?)(\\end\{tabular\})'
        match = re.search(pattern, self._latex, re.DOTALL)
        if not match:
            return self
        begin_tabular, star, col_spec, content, end_tabular = match.groups()
        if star == '*' and r'\extracolsep' in col_spec:
            return self
        inner_col_spec = col_spec[1:-1]
        new_col_spec = f'{{@{{\\extracolsep{{\\fill}}}}{inner_col_spec}}}'
        new_tabular = f'\\begin{{tabular*}}{{\\textwidth}}{new_col_spec}'
        new_end = f'\\end{{tabular*}}'
        self._latex = self._latex.replace(begin_tabular + star + col_spec, new_tabular)
        self._latex = self._latex.replace(end_tabular, new_end)
        return self

    def escape(self):
        """Escape LaTeX special characters (uses original latex_escape logic)."""
        s = self._latex
        if not isinstance(s, str):
            s = str(s)
        replacements = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
            '<': r'\textless{}',
            '>': r'\textgreater{}',
        }
        for char, escaped in replacements.items():
            s = s.replace(char, escaped)
        self._latex = s
        return self

    def set_equal_column_widths(self, align='c', extra_padding=2, stretch_first=False, other_width='2cm'):
        r"""Set all columns to equal width (or stretch first column) using full \linewidth.

        If stretch_first=False (default): all columns get equal static width.
        If stretch_first=True: first column becomes X (stretches), others use 'align'.
        """
        lines = self._latex.split('\n')
        in_tabular = False
        first_data_row = None
        for line in lines:
            if '\\begin{tabular' in line:
                in_tabular = True
                continue
            if in_tabular and line.strip() and not line.strip().startswith('%'):
                if '&' in line:
                    first_data_row = line
                    break
        if first_data_row is None:
            return self

        num_cols = first_data_row.count('&') + 1
        if num_cols == 0:
            return self

        if stretch_first and num_cols > 1:
            # Build column spec: X for first column, then (num_cols-1) times p{...} with equal width
            col_spec = 'X' + f'p{{{other_width}}}' * (num_cols - 1)

            pattern = r'(\\begin\{tabular\*?\})(?:\[[^\]]*\])?(\{[^}]+\})'
            # Use a lambda to avoid backslash escape processing in the replacement
            self._latex = re.sub(pattern,
                                 lambda m: '\\begin{tabularx}{\\linewidth}{' + col_spec + '}',
                                 self._latex, count=1)
            # Change the closing environment
            self._latex = self._latex.replace('\\end{tabular}', '\\end{tabularx}', 1)
        else:
            # Original equal-width behaviour (works without extra packages)
            col_width = f'\\dimexpr \\linewidth/{num_cols} - 2\\tabcolsep\\relax'
            new_col_spec = '@{}' + f'p{{{col_width}}}' * num_cols + '@{}'
            pattern = r'(\\begin\{tabular\*?\})(?:\[[^\]]*\])?(\{[^}]+\})'
            self._latex = re.sub(pattern,
                                 lambda m: m.group(1) + '{' + new_col_spec + '}',
                                 self._latex, count=1)
        return self

def format_address(address: str) -> str:
    """
    Convert an address string to a clean, properly capitalized format.

    Example:
        Input:  "270 PARK AVENUE, NEW YORK, NY, UNITED STATES, 10017"
        Output: "270 Park Avenue, New York, NY, United States, 10017"
    """
    # Split by comma, strip whitespace, and capitalize each part
    parts = [part.strip().title() for part in address.split(',')]

    # Special handling for US state abbreviations (keep them uppercase)
    # e.g., "Ny" -> "NY", "Ca" -> "CA"
    for i, part in enumerate(parts):
        if len(part) == 2 and part.isalpha():
            parts[i] = part.upper()

    # Join back with comma + space
    return ', '.join(parts)

def latex_escape(s):
    if not isinstance(s, str):
        s = str(s)
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    for char, escaped in replacements.items():
        s = s.replace(char, escaped)
    return s