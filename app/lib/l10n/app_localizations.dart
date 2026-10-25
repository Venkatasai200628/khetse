import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_te.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('te'),
  ];

  /// No description provided for @tagline.
  ///
  /// In en, this message translates to:
  /// **'Seedha Khet Se Ghar Tak'**
  String get tagline;

  /// No description provided for @chooseLanguage.
  ///
  /// In en, this message translates to:
  /// **'Choose language'**
  String get chooseLanguage;

  /// No description provided for @languageSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Select the language you are comfortable with. You can change it anytime from your profile.'**
  String get languageSubtitle;

  /// No description provided for @continueLabel.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueLabel;

  /// No description provided for @welcomeTitle.
  ///
  /// In en, this message translates to:
  /// **'Fresh from the farm, direct to you'**
  String get welcomeTitle;

  /// No description provided for @welcomeSubtitle.
  ///
  /// In en, this message translates to:
  /// **'KhetSe connects farmers directly with households and businesses — no middlemen, fair prices for everyone.'**
  String get welcomeSubtitle;

  /// No description provided for @roleFarmer.
  ///
  /// In en, this message translates to:
  /// **'Farmer'**
  String get roleFarmer;

  /// No description provided for @roleFarmerDesc.
  ///
  /// In en, this message translates to:
  /// **'List your harvest and sell directly at fair prices'**
  String get roleFarmerDesc;

  /// No description provided for @roleBuyer.
  ///
  /// In en, this message translates to:
  /// **'Buyer'**
  String get roleBuyer;

  /// No description provided for @roleBuyerDesc.
  ///
  /// In en, this message translates to:
  /// **'Browse farm-fresh produce and order to your door'**
  String get roleBuyerDesc;

  /// No description provided for @roleDriver.
  ///
  /// In en, this message translates to:
  /// **'Driver'**
  String get roleDriver;

  /// No description provided for @roleDriverDesc.
  ///
  /// In en, this message translates to:
  /// **'Deliver farm produce with QR-verified handoffs'**
  String get roleDriverDesc;

  /// No description provided for @roleFpo.
  ///
  /// In en, this message translates to:
  /// **'FPO / Collection centre'**
  String get roleFpo;

  /// No description provided for @roleFpoDesc.
  ///
  /// In en, this message translates to:
  /// **'Aggregate member farmers\' orders and dispatch'**
  String get roleFpoDesc;

  /// No description provided for @roleAdmin.
  ///
  /// In en, this message translates to:
  /// **'Admin console'**
  String get roleAdmin;

  /// No description provided for @loginTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in with your mobile'**
  String get loginTitle;

  /// No description provided for @loginSubtitle.
  ///
  /// In en, this message translates to:
  /// **'We\'ll send a one-time password (OTP) to verify your number.'**
  String get loginSubtitle;

  /// No description provided for @phoneNumber.
  ///
  /// In en, this message translates to:
  /// **'Mobile number'**
  String get phoneNumber;

  /// No description provided for @sendOtp.
  ///
  /// In en, this message translates to:
  /// **'Send OTP'**
  String get sendOtp;

  /// No description provided for @enterOtp.
  ///
  /// In en, this message translates to:
  /// **'Enter the OTP'**
  String get enterOtp;

  /// No description provided for @otpSentTo.
  ///
  /// In en, this message translates to:
  /// **'Code sent to'**
  String get otpSentTo;

  /// No description provided for @otpLabel.
  ///
  /// In en, this message translates to:
  /// **'6-digit code'**
  String get otpLabel;

  /// No description provided for @demoOtpPrefix.
  ///
  /// In en, this message translates to:
  /// **'Demo OTP'**
  String get demoOtpPrefix;

  /// No description provided for @tapToFill.
  ///
  /// In en, this message translates to:
  /// **'tap to fill'**
  String get tapToFill;

  /// No description provided for @verify.
  ///
  /// In en, this message translates to:
  /// **'Verify & continue'**
  String get verify;

  /// No description provided for @changeNumber.
  ///
  /// In en, this message translates to:
  /// **'Use a different number'**
  String get changeNumber;

  /// No description provided for @demoDivider.
  ///
  /// In en, this message translates to:
  /// **'or continue with a demo account'**
  String get demoDivider;

  /// No description provided for @demoLoginAs.
  ///
  /// In en, this message translates to:
  /// **'Sign in as'**
  String get demoLoginAs;

  /// No description provided for @demoNote.
  ///
  /// In en, this message translates to:
  /// **'Demo accounts exist only while the backend runs in demo mode; they never work in production.'**
  String get demoNote;

  /// No description provided for @registerTitle.
  ///
  /// In en, this message translates to:
  /// **'Complete your registration'**
  String get registerTitle;

  /// No description provided for @fullName.
  ///
  /// In en, this message translates to:
  /// **'Full name'**
  String get fullName;

  /// No description provided for @iAmA.
  ///
  /// In en, this message translates to:
  /// **'I am a'**
  String get iAmA;

  /// No description provided for @createAccount.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get createAccount;

  /// No description provided for @registerNote.
  ///
  /// In en, this message translates to:
  /// **'FPO operator and admin accounts are provisioned by the platform team.'**
  String get registerNote;

  /// No description provided for @navHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get navHome;

  /// No description provided for @navShop.
  ///
  /// In en, this message translates to:
  /// **'Shop'**
  String get navShop;

  /// No description provided for @navCart.
  ///
  /// In en, this message translates to:
  /// **'Cart'**
  String get navCart;

  /// No description provided for @navOrders.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get navOrders;

  /// No description provided for @navListings.
  ///
  /// In en, this message translates to:
  /// **'Listings'**
  String get navListings;

  /// No description provided for @navProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get navProfile;

  /// No description provided for @navOverview.
  ///
  /// In en, this message translates to:
  /// **'Overview'**
  String get navOverview;

  /// No description provided for @navTrips.
  ///
  /// In en, this message translates to:
  /// **'Trips'**
  String get navTrips;

  /// No description provided for @hello.
  ///
  /// In en, this message translates to:
  /// **'Namaste'**
  String get hello;

  /// No description provided for @farmerHeaderSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Sell your harvest directly — no middlemen.'**
  String get farmerHeaderSubtitle;

  /// No description provided for @statLiveListings.
  ///
  /// In en, this message translates to:
  /// **'Live listings'**
  String get statLiveListings;

  /// No description provided for @statTotalListings.
  ///
  /// In en, this message translates to:
  /// **'Total listings'**
  String get statTotalListings;

  /// No description provided for @createListing.
  ///
  /// In en, this message translates to:
  /// **'Create listing'**
  String get createListing;

  /// No description provided for @createListingSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Tell buyers what you harvested. Prices are per unit and entered in rupees.'**
  String get createListingSubtitle;

  /// No description provided for @recentOrders.
  ///
  /// In en, this message translates to:
  /// **'Recent orders'**
  String get recentOrders;

  /// No description provided for @noOrdersTitle.
  ///
  /// In en, this message translates to:
  /// **'No orders yet'**
  String get noOrdersTitle;

  /// No description provided for @farmerNoOrders.
  ///
  /// In en, this message translates to:
  /// **'When buyers order your produce, the request appears here for you to accept or reject.'**
  String get farmerNoOrders;

  /// No description provided for @incomingOrders.
  ///
  /// In en, this message translates to:
  /// **'Incoming orders'**
  String get incomingOrders;

  /// No description provided for @incomingOrdersSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Accept or reject each order — buyers are notified instantly.'**
  String get incomingOrdersSubtitle;

  /// No description provided for @myListings.
  ///
  /// In en, this message translates to:
  /// **'My listings'**
  String get myListings;

  /// No description provided for @noListingsTitle.
  ///
  /// In en, this message translates to:
  /// **'No listings yet'**
  String get noListingsTitle;

  /// No description provided for @noListingsMessage.
  ///
  /// In en, this message translates to:
  /// **'Create your first listing so buyers can find your produce.'**
  String get noListingsMessage;

  /// No description provided for @crop.
  ///
  /// In en, this message translates to:
  /// **'Crop'**
  String get crop;

  /// No description provided for @quantity.
  ///
  /// In en, this message translates to:
  /// **'Quantity'**
  String get quantity;

  /// No description provided for @unitLabel.
  ///
  /// In en, this message translates to:
  /// **'Unit'**
  String get unitLabel;

  /// No description provided for @pricePer.
  ///
  /// In en, this message translates to:
  /// **'Price per'**
  String get pricePer;

  /// No description provided for @priceHelper.
  ///
  /// In en, this message translates to:
  /// **'You can adjust the price anytime while the listing is live.'**
  String get priceHelper;

  /// No description provided for @enterQuantity.
  ///
  /// In en, this message translates to:
  /// **'Enter the quantity'**
  String get enterQuantity;

  /// No description provided for @enterPrice.
  ///
  /// In en, this message translates to:
  /// **'Enter your price'**
  String get enterPrice;

  /// No description provided for @qualityGrade.
  ///
  /// In en, this message translates to:
  /// **'Quality grade'**
  String get qualityGrade;

  /// No description provided for @harvestDate.
  ///
  /// In en, this message translates to:
  /// **'Harvest date'**
  String get harvestDate;

  /// No description provided for @today.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get today;

  /// No description provided for @descriptionOptional.
  ///
  /// In en, this message translates to:
  /// **'Description (optional)'**
  String get descriptionOptional;

  /// No description provided for @publish.
  ///
  /// In en, this message translates to:
  /// **'Publish listing'**
  String get publish;

  /// No description provided for @commodityLoadFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not load the crop catalogue'**
  String get commodityLoadFailed;

  /// No description provided for @shopTitle.
  ///
  /// In en, this message translates to:
  /// **'Farm shop'**
  String get shopTitle;

  /// No description provided for @shopSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Fresh produce listed directly by farmers nearby.'**
  String get shopSubtitle;

  /// No description provided for @searchHint.
  ///
  /// In en, this message translates to:
  /// **'Search tomatoes, rice, milk…'**
  String get searchHint;

  /// No description provided for @noListingsFoundTitle.
  ///
  /// In en, this message translates to:
  /// **'Nothing to show'**
  String get noListingsFoundTitle;

  /// No description provided for @shopEmptyMessage.
  ///
  /// In en, this message translates to:
  /// **'No live listings right now. Check back soon — new harvest arrives daily.'**
  String get shopEmptyMessage;

  /// No description provided for @searchEmptyMessage.
  ///
  /// In en, this message translates to:
  /// **'No listings match your search. Try a different word.'**
  String get searchEmptyMessage;

  /// No description provided for @clearSearch.
  ///
  /// In en, this message translates to:
  /// **'Clear search'**
  String get clearSearch;

  /// No description provided for @listingDetail.
  ///
  /// In en, this message translates to:
  /// **'Listing'**
  String get listingDetail;

  /// No description provided for @available.
  ///
  /// In en, this message translates to:
  /// **'Available'**
  String get available;

  /// No description provided for @grade.
  ///
  /// In en, this message translates to:
  /// **'Grade'**
  String get grade;

  /// No description provided for @harvested.
  ///
  /// In en, this message translates to:
  /// **'Harvested'**
  String get harvested;

  /// No description provided for @demoDataLabel.
  ///
  /// In en, this message translates to:
  /// **'Demo data — labelled synthetic by the backend'**
  String get demoDataLabel;

  /// No description provided for @addToCart.
  ///
  /// In en, this message translates to:
  /// **'Add to cart'**
  String get addToCart;

  /// No description provided for @soldOut.
  ///
  /// In en, this message translates to:
  /// **'This listing is sold out.'**
  String get soldOut;

  /// No description provided for @listingNotAvailable.
  ///
  /// In en, this message translates to:
  /// **'This listing is no longer available.'**
  String get listingNotAvailable;

  /// No description provided for @addedToCart.
  ///
  /// In en, this message translates to:
  /// **'Added to cart'**
  String get addedToCart;

  /// No description provided for @cartEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'Your cart is empty'**
  String get cartEmptyTitle;

  /// No description provided for @cartEmptyMessage.
  ///
  /// In en, this message translates to:
  /// **'Add fresh produce from the shop and it will show up here.'**
  String get cartEmptyMessage;

  /// No description provided for @browseProduce.
  ///
  /// In en, this message translates to:
  /// **'Browse produce'**
  String get browseProduce;

  /// No description provided for @subtotal.
  ///
  /// In en, this message translates to:
  /// **'Subtotal'**
  String get subtotal;

  /// No description provided for @feesAtCheckout.
  ///
  /// In en, this message translates to:
  /// **'Delivery and platform fees are computed by the server at checkout.'**
  String get feesAtCheckout;

  /// No description provided for @checkout.
  ///
  /// In en, this message translates to:
  /// **'Checkout'**
  String get checkout;

  /// No description provided for @deliveryFeesNote.
  ///
  /// In en, this message translates to:
  /// **'Delivery fee, platform fee and the final total are calculated by the backend at checkout.'**
  String get deliveryFeesNote;

  /// No description provided for @address.
  ///
  /// In en, this message translates to:
  /// **'Delivery address'**
  String get address;

  /// No description provided for @district.
  ///
  /// In en, this message translates to:
  /// **'District'**
  String get district;

  /// No description provided for @enterName.
  ///
  /// In en, this message translates to:
  /// **'Enter the receiver\'s name'**
  String get enterName;

  /// No description provided for @enterPhone.
  ///
  /// In en, this message translates to:
  /// **'Enter a 10-digit mobile number'**
  String get enterPhone;

  /// No description provided for @enterAddress.
  ///
  /// In en, this message translates to:
  /// **'Enter the delivery address'**
  String get enterAddress;

  /// No description provided for @enterDistrict.
  ///
  /// In en, this message translates to:
  /// **'Enter the district'**
  String get enterDistrict;

  /// No description provided for @notesOptional.
  ///
  /// In en, this message translates to:
  /// **'Delivery notes (optional)'**
  String get notesOptional;

  /// No description provided for @placeOrder.
  ///
  /// In en, this message translates to:
  /// **'Place order'**
  String get placeOrder;

  /// No description provided for @myOrders.
  ///
  /// In en, this message translates to:
  /// **'My orders'**
  String get myOrders;

  /// No description provided for @myOrdersSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Track every order from farm to door.'**
  String get myOrdersSubtitle;

  /// No description provided for @buyerNoOrders.
  ///
  /// In en, this message translates to:
  /// **'Your first order will appear here once you check out.'**
  String get buyerNoOrders;

  /// No description provided for @upcomingTrips.
  ///
  /// In en, this message translates to:
  /// **'Assigned trips'**
  String get upcomingTrips;

  /// No description provided for @noTripsTitle.
  ///
  /// In en, this message translates to:
  /// **'No trips assigned'**
  String get noTripsTitle;

  /// No description provided for @noTripsMessage.
  ///
  /// In en, this message translates to:
  /// **'When the FPO assigns you a delivery run, the manifest and stops will appear here.'**
  String get noTripsMessage;

  /// No description provided for @driverHeaderSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Shared delivery runs with QR-verified handoffs.'**
  String get driverHeaderSubtitle;

  /// No description provided for @verificationStatus.
  ///
  /// In en, this message translates to:
  /// **'Verification'**
  String get verificationStatus;

  /// No description provided for @verified.
  ///
  /// In en, this message translates to:
  /// **'Verified'**
  String get verified;

  /// No description provided for @driverPhaseNote.
  ///
  /// In en, this message translates to:
  /// **'Shipment and dispatch endpoints are the next build phase (ANALYSIS.md §9, Phase 4). This dashboard shows your real profile and will pick up trips the moment those endpoints ship.'**
  String get driverPhaseNote;

  /// No description provided for @fpoOrdersTitle.
  ///
  /// In en, this message translates to:
  /// **'Member orders'**
  String get fpoOrdersTitle;

  /// No description provided for @fpoOrdersSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Orders containing your member farmers\' listings.'**
  String get fpoOrdersSubtitle;

  /// No description provided for @fpoNoOrders.
  ///
  /// In en, this message translates to:
  /// **'Orders from member farmers will appear here once buyers start purchasing.'**
  String get fpoNoOrders;

  /// No description provided for @fpoOrderCount.
  ///
  /// In en, this message translates to:
  /// **'Orders involving your members'**
  String get fpoOrderCount;

  /// No description provided for @adminOverviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Platform overview'**
  String get adminOverviewTitle;

  /// No description provided for @adminOverviewSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Live counts computed from the marketplace API.'**
  String get adminOverviewSubtitle;

  /// No description provided for @adminTotalListings.
  ///
  /// In en, this message translates to:
  /// **'Total listings'**
  String get adminTotalListings;

  /// No description provided for @adminLiveListings.
  ///
  /// In en, this message translates to:
  /// **'Live listings'**
  String get adminLiveListings;

  /// No description provided for @adminDistricts.
  ///
  /// In en, this message translates to:
  /// **'Districts'**
  String get adminDistricts;

  /// No description provided for @adminCommodities.
  ///
  /// In en, this message translates to:
  /// **'Commodities'**
  String get adminCommodities;

  /// No description provided for @adminAvgListed.
  ///
  /// In en, this message translates to:
  /// **'Average listed price'**
  String get adminAvgListed;

  /// No description provided for @adminSampleNote.
  ///
  /// In en, this message translates to:
  /// **'Computed from the first 100 listing rows returned by the API — an honest sample, not a full database aggregate.'**
  String get adminSampleNote;

  /// No description provided for @adminTopCommodities.
  ///
  /// In en, this message translates to:
  /// **'Top commodities'**
  String get adminTopCommodities;

  /// No description provided for @accountStatus.
  ///
  /// In en, this message translates to:
  /// **'Account status'**
  String get accountStatus;

  /// No description provided for @active.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get active;

  /// No description provided for @memberSince.
  ///
  /// In en, this message translates to:
  /// **'Member since'**
  String get memberSince;

  /// No description provided for @preferences.
  ///
  /// In en, this message translates to:
  /// **'Preferences'**
  String get preferences;

  /// No description provided for @appLanguage.
  ///
  /// In en, this message translates to:
  /// **'App language'**
  String get appLanguage;

  /// No description provided for @about.
  ///
  /// In en, this message translates to:
  /// **'About'**
  String get about;

  /// No description provided for @apiEndpoint.
  ///
  /// In en, this message translates to:
  /// **'API endpoint'**
  String get apiEndpoint;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get logout;

  /// No description provided for @logoutConfirm.
  ///
  /// In en, this message translates to:
  /// **'You\'ll need to sign in again with your mobile number.'**
  String get logoutConfirm;

  /// No description provided for @stay.
  ///
  /// In en, this message translates to:
  /// **'Stay'**
  String get stay;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'te'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'te':
      return AppLocalizationsTe();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
