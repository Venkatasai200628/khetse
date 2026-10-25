/// Money helpers. The backend stores every amount in integer paise
/// (₹1 = 100) — never floats (ANALYSIS.md §11 red line).
library;

/// Formats paise as a rupee string with Indian digit grouping.
///
/// Example: `123456` → `₹1,234.56`, `5000` → `₹50`.
String formatPaise(int paise, {bool withSymbol = true}) {
  final negative = paise < 0;
  final abs = paise.abs();
  final rupees = abs ~/ 100;
  final remainder = (abs % 100).toString().padLeft(2, '0');

  final grouped = _groupIndian(rupees.toString());
  final value = remainder == '00'
      ? grouped
      : '$grouped.$remainder';
  final sign = negative ? '-' : '';
  return withSymbol ? '$sign₹$value' : sign + value;
}

/// Indian grouping: first group of 1-2 digits, then groups of 2
/// (1,23,45,678). The first group is 1 digit only when the remaining
/// digits are odd in count, e.g. `1234` → `1,234`.
String _groupIndian(String digits) {
  if (digits.length <= 3) return digits;
  final last3 = digits.substring(digits.length - 3);
  final rest = digits.substring(0, digits.length - 3);
  final firstLen = rest.length % 2 == 0 ? 2 : 1;
  final buffer = StringBuffer()..write(rest.substring(0, firstLen));
  for (var i = firstLen; i < rest.length; i += 2) {
    buffer.write(',');
    buffer.write(rest.substring(i, i + 2));
  }
  return '$buffer,$last3';
}

/// Converts a rupee amount entered by the user into integer paise.
int rupeesToPaise(double rupees) => (rupees * 100).round();
