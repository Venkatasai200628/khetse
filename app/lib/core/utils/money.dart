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

/// Indian grouping: last 3 digits, then groups of 2 (1,23,45,678).
String _groupIndian(String digits) {
  if (digits.length <= 3) return digits;
  final last3 = digits.substring(digits.length - 3);
  final rest = digits.substring(0, digits.length - 3);
  final buffer = StringBuffer();
  final remainder = rest.length % 2;
  if (remainder == 1) {
    buffer.write(rest[0]);
    buffer.write(',');
  }
  for (var i = remainder; i < rest.length; i += 2) {
    buffer.write(rest.substring(i, i + 2));
    if (i + 2 < rest.length) buffer.write(',');
  }
  return '$buffer,$last3';
}

/// Converts a rupee amount entered by the user into integer paise.
int rupeesToPaise(double rupees) => (rupees * 100).round();
