/// Small date helpers (no heavy deps) for friendly timestamps.
library;

const _months = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/// `2026-10-25T09:30:00` → `25 Oct 2026, 9:30 AM`.
String formatDateTime(DateTime dt) {
  final hour = dt.hour == 0
      ? 12
      : dt.hour > 12
          ? dt.hour - 12
          : dt.hour;
  final amPm = dt.hour < 12 ? 'AM' : 'PM';
  final minute = dt.minute.toString().padLeft(2, '0');
  return '${dt.day} ${_months[dt.month - 1]} ${dt.year}, $hour:$minute $amPm';
}

/// `2026-10-25` → `25 Oct 2026`.
String formatDate(DateTime dt) =>
    '${dt.day} ${_months[dt.month - 1]} ${dt.year}';

/// Relative-ish label: Today / Yesterday / n days ago / date.
String formatRelative(DateTime dt) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(dt.year, dt.month, dt.day);
  final diff = today.difference(day).inDays;
  if (diff == 0) return 'Today';
  if (diff == 1) return 'Yesterday';
  if (diff > 1 && diff < 7) return '$diff days ago';
  return formatDate(dt);
}
