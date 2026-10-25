// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get tagline => 'Seedha Khet Se Ghar Tak';

  @override
  String get chooseLanguage => 'Choose language';

  @override
  String get languageSubtitle =>
      'Select the language you are comfortable with. You can change it anytime from your profile.';

  @override
  String get continueLabel => 'Continue';

  @override
  String get welcomeTitle => 'Fresh from the farm, direct to you';

  @override
  String get welcomeSubtitle =>
      'KhetSe connects farmers directly with households and businesses — no middlemen, fair prices for everyone.';

  @override
  String get roleFarmer => 'Farmer';

  @override
  String get roleFarmerDesc =>
      'List your harvest and sell directly at fair prices';

  @override
  String get roleBuyer => 'Buyer';

  @override
  String get roleBuyerDesc =>
      'Browse farm-fresh produce and order to your door';

  @override
  String get roleDriver => 'Driver';

  @override
  String get roleDriverDesc => 'Deliver farm produce with QR-verified handoffs';

  @override
  String get roleFpo => 'FPO / Collection centre';

  @override
  String get roleFpoDesc => 'Aggregate member farmers\' orders and dispatch';

  @override
  String get roleAdmin => 'Admin console';

  @override
  String get loginTitle => 'Sign in with your mobile';

  @override
  String get loginSubtitle =>
      'We\'ll send a one-time password (OTP) to verify your number.';

  @override
  String get phoneNumber => 'Mobile number';

  @override
  String get sendOtp => 'Send OTP';

  @override
  String get enterOtp => 'Enter the OTP';

  @override
  String get otpSentTo => 'Code sent to';

  @override
  String get otpLabel => '6-digit code';

  @override
  String get demoOtpPrefix => 'Demo OTP';

  @override
  String get tapToFill => 'tap to fill';

  @override
  String get verify => 'Verify & continue';

  @override
  String get changeNumber => 'Use a different number';

  @override
  String get demoDivider => 'or continue with a demo account';

  @override
  String get demoLoginAs => 'Sign in as';

  @override
  String get demoNote =>
      'Demo accounts exist only while the backend runs in demo mode; they never work in production.';

  @override
  String get registerTitle => 'Complete your registration';

  @override
  String get fullName => 'Full name';

  @override
  String get iAmA => 'I am a';

  @override
  String get createAccount => 'Create account';

  @override
  String get registerNote =>
      'FPO operator and admin accounts are provisioned by the platform team.';

  @override
  String get navHome => 'Home';

  @override
  String get navShop => 'Shop';

  @override
  String get navCart => 'Cart';

  @override
  String get navOrders => 'Orders';

  @override
  String get navListings => 'Listings';

  @override
  String get navProfile => 'Profile';

  @override
  String get navOverview => 'Overview';

  @override
  String get navTrips => 'Trips';

  @override
  String get hello => 'Namaste';

  @override
  String get farmerHeaderSubtitle =>
      'Sell your harvest directly — no middlemen.';

  @override
  String get statLiveListings => 'Live listings';

  @override
  String get statTotalListings => 'Total listings';

  @override
  String get createListing => 'Create listing';

  @override
  String get createListingSubtitle =>
      'Tell buyers what you harvested. Prices are per unit and entered in rupees.';

  @override
  String get recentOrders => 'Recent orders';

  @override
  String get noOrdersTitle => 'No orders yet';

  @override
  String get farmerNoOrders =>
      'When buyers order your produce, the request appears here for you to accept or reject.';

  @override
  String get incomingOrders => 'Incoming orders';

  @override
  String get incomingOrdersSubtitle =>
      'Accept or reject each order — buyers are notified instantly.';

  @override
  String get myListings => 'My listings';

  @override
  String get noListingsTitle => 'No listings yet';

  @override
  String get noListingsMessage =>
      'Create your first listing so buyers can find your produce.';

  @override
  String get crop => 'Crop';

  @override
  String get quantity => 'Quantity';

  @override
  String get unitLabel => 'Unit';

  @override
  String get pricePer => 'Price per';

  @override
  String get priceHelper =>
      'You can adjust the price anytime while the listing is live.';

  @override
  String get enterQuantity => 'Enter the quantity';

  @override
  String get enterPrice => 'Enter your price';

  @override
  String get qualityGrade => 'Quality grade';

  @override
  String get harvestDate => 'Harvest date';

  @override
  String get today => 'Today';

  @override
  String get descriptionOptional => 'Description (optional)';

  @override
  String get publish => 'Publish listing';

  @override
  String get commodityLoadFailed => 'Could not load the crop catalogue';

  @override
  String get shopTitle => 'Farm shop';

  @override
  String get shopSubtitle => 'Fresh produce listed directly by farmers nearby.';

  @override
  String get searchHint => 'Search tomatoes, rice, milk…';

  @override
  String get noListingsFoundTitle => 'Nothing to show';

  @override
  String get shopEmptyMessage =>
      'No live listings right now. Check back soon — new harvest arrives daily.';

  @override
  String get searchEmptyMessage =>
      'No listings match your search. Try a different word.';

  @override
  String get clearSearch => 'Clear search';

  @override
  String get listingDetail => 'Listing';

  @override
  String get available => 'Available';

  @override
  String get grade => 'Grade';

  @override
  String get harvested => 'Harvested';

  @override
  String get demoDataLabel => 'Demo data — labelled synthetic by the backend';

  @override
  String get addToCart => 'Add to cart';

  @override
  String get soldOut => 'This listing is sold out.';

  @override
  String get listingNotAvailable => 'This listing is no longer available.';

  @override
  String get addedToCart => 'Added to cart';

  @override
  String get cartEmptyTitle => 'Your cart is empty';

  @override
  String get cartEmptyMessage =>
      'Add fresh produce from the shop and it will show up here.';

  @override
  String get browseProduce => 'Browse produce';

  @override
  String get subtotal => 'Subtotal';

  @override
  String get feesAtCheckout =>
      'Delivery and platform fees are computed by the server at checkout.';

  @override
  String get checkout => 'Checkout';

  @override
  String get deliveryFeesNote =>
      'Delivery fee, platform fee and the final total are calculated by the backend at checkout.';

  @override
  String get address => 'Delivery address';

  @override
  String get district => 'District';

  @override
  String get enterName => 'Enter the receiver\'s name';

  @override
  String get enterPhone => 'Enter a 10-digit mobile number';

  @override
  String get enterAddress => 'Enter the delivery address';

  @override
  String get enterDistrict => 'Enter the district';

  @override
  String get notesOptional => 'Delivery notes (optional)';

  @override
  String get placeOrder => 'Place order';

  @override
  String get myOrders => 'My orders';

  @override
  String get myOrdersSubtitle => 'Track every order from farm to door.';

  @override
  String get buyerNoOrders =>
      'Your first order will appear here once you check out.';

  @override
  String get upcomingTrips => 'Assigned trips';

  @override
  String get noTripsTitle => 'No trips assigned';

  @override
  String get noTripsMessage =>
      'When the FPO assigns you a delivery run, the manifest and stops will appear here.';

  @override
  String get driverHeaderSubtitle =>
      'Shared delivery runs with QR-verified handoffs.';

  @override
  String get verificationStatus => 'Verification';

  @override
  String get verified => 'Verified';

  @override
  String get driverPhaseNote =>
      'Shipment and dispatch endpoints are the next build phase (ANALYSIS.md §9, Phase 4). This dashboard shows your real profile and will pick up trips the moment those endpoints ship.';

  @override
  String get fpoOrdersTitle => 'Member orders';

  @override
  String get fpoOrdersSubtitle =>
      'Orders containing your member farmers\' listings.';

  @override
  String get fpoNoOrders =>
      'Orders from member farmers will appear here once buyers start purchasing.';

  @override
  String get fpoOrderCount => 'Orders involving your members';

  @override
  String get adminOverviewTitle => 'Platform overview';

  @override
  String get adminOverviewSubtitle =>
      'Live counts computed from the marketplace API.';

  @override
  String get adminTotalListings => 'Total listings';

  @override
  String get adminLiveListings => 'Live listings';

  @override
  String get adminDistricts => 'Districts';

  @override
  String get adminCommodities => 'Commodities';

  @override
  String get adminAvgListed => 'Average listed price';

  @override
  String get adminSampleNote =>
      'Computed from the first 100 listing rows returned by the API — an honest sample, not a full database aggregate.';

  @override
  String get adminTopCommodities => 'Top commodities';

  @override
  String get accountStatus => 'Account status';

  @override
  String get active => 'Active';

  @override
  String get memberSince => 'Member since';

  @override
  String get preferences => 'Preferences';

  @override
  String get appLanguage => 'App language';

  @override
  String get about => 'About';

  @override
  String get apiEndpoint => 'API endpoint';

  @override
  String get logout => 'Log out';

  @override
  String get logoutConfirm =>
      'You\'ll need to sign in again with your mobile number.';

  @override
  String get stay => 'Stay';
}
