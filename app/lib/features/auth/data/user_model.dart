/// User + role models mirroring `backend/app/schemas/auth.py` (UserPublic).
class AppUser {
  AppUser({
    required this.id,
    required this.phone,
    required this.fullName,
    required this.preferredLanguage,
    required this.status,
    required this.roles,
    required this.createdAt,
  });

  final String id;
  final String phone;
  final String? fullName;
  final String preferredLanguage;
  final String status;
  final List<String> roles;
  final DateTime createdAt;

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as String,
        phone: json['phone'] as String,
        fullName: json['full_name'] as String?,
        preferredLanguage: (json['preferred_language'] ?? 'en') as String,
        status: (json['status'] ?? 'pending') as String,
        roles: (json['roles'] as List? ?? [])
            .map((e) => e.toString())
            .toList(),
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
            DateTime.now(),
      );

  String get displayName => (fullName == null || fullName!.trim().isEmpty)
      ? 'KhetSe user'
      : fullName!.trim();

  /// Picks the shell this user should land in after login.
  AppRole get primaryRole {
    for (final role in roles) {
      switch (role) {
        case 'farmer':
          return AppRole.farmer;
        case 'buyer':
        case 'business':
          return AppRole.buyer;
        case 'driver':
          return AppRole.driver;
        case 'fpo_operator':
          return AppRole.fpo;
        case 'admin':
          return AppRole.admin;
      }
    }
    return AppRole.buyer;
  }
}

enum AppRole {
  farmer('/farmer'),
  buyer('/buyer'),
  driver('/driver'),
  fpo('/fpo'),
  admin('/admin');

  const AppRole(this.homePath);
  final String homePath;
}
