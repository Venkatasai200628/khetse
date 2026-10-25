import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';

/// Payment endpoints — `backend/app/api/v1/payments.py`.
///
/// The sandbox flow is explicit: initiate opens a mock transaction, confirm
/// is the simulated provider webhook. Money only becomes `success` after the
/// confirm call, and every transaction row is labelled `is_sandbox: true`.
class PaymentApi {
  PaymentApi(this._dio);
  final Dio _dio;

  /// GET /payments/orders/{id} — payment status, breakdown and ledger lines
  /// (owner or admin only).
  Future<OrderPayment> forOrder(String orderId) async {
    final res = await guard<Response>(() => _dio.get('/payments/orders/$orderId'));
    throwIfError(res);
    return OrderPayment.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /payments/orders/{id}/initiate — opens the sandbox transaction.
  Future<PaymentTransaction> initiate(String orderId) async {
    final res = await guard<Response>(
      () => _dio.post('/payments/orders/$orderId/initiate'),
    );
    throwIfError(res);
    return PaymentTransaction.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /payments/transactions/{id}/confirm — simulated provider webhook.
  /// Idempotent: a double confirm returns the first settlement untouched.
  Future<ConfirmResult> confirm(String transactionId) async {
    final res = await guard<Response>(
      () => _dio.post('/payments/transactions/$transactionId/confirm'),
    );
    throwIfError(res);
    return ConfirmResult.fromJson(res.data as Map<String, dynamic>);
  }
}

/// PaymentTransaction — mirrors `PaymentTransactionPublic`.
class PaymentTransaction {
  PaymentTransaction({
    required this.id,
    required this.orderId,
    required this.provider,
    required this.amountPaise,
    required this.currency,
    required this.status,
    required this.isSandbox,
  });

  final String id;
  final String orderId;
  final String provider;
  final int amountPaise;
  final String currency;
  final String status;
  final bool isSandbox;

  bool get isSuccessful => status.toLowerCase() == 'success';

  factory PaymentTransaction.fromJson(Map<String, dynamic> json) =>
      PaymentTransaction(
        id: json['id'] as String,
        orderId: json['order_id'] as String,
        provider: (json['provider'] ?? 'mock') as String,
        amountPaise: (json['amount_paise'] ?? 0) as int,
        currency: (json['currency'] ?? 'INR') as String,
        status: (json['status'] ?? 'initiated') as String,
        isSandbox: (json['is_sandbox'] ?? false) as bool,
      );
}

/// LedgerEntry — mirrors `LedgerEntryPublic`.
class LedgerLine {
  LedgerLine({
    required this.entryType,
    required this.debitAccount,
    required this.creditAccount,
    required this.amountPaise,
    required this.memo,
  });

  final String entryType;
  final String debitAccount;
  final String creditAccount;
  final int amountPaise;
  final String? memo;

  factory LedgerLine.fromJson(Map<String, dynamic> json) => LedgerLine(
        entryType: (json['entry_type'] ?? '') as String,
        debitAccount: (json['debit_account'] ?? '') as String,
        creditAccount: (json['credit_account'] ?? '') as String,
        amountPaise: (json['amount_paise'] ?? 0) as int,
        memo: json['memo'] as String?,
      );
}

/// GET /payments/orders/{id} response — mirrors `OrderPaymentResponse`.
class OrderPayment {
  OrderPayment({
    required this.orderId,
    required this.orderStatus,
    required this.paymentStatus,
    required this.subtotalPaise,
    required this.deliveryFeePaise,
    required this.platformFeePaise,
    required this.totalPaise,
    required this.currency,
    required this.transactions,
    required this.ledgerEntries,
  });

  final String orderId;
  final String orderStatus;
  final String paymentStatus;
  final int subtotalPaise;
  final int deliveryFeePaise;
  final int platformFeePaise;
  final int totalPaise;
  final String currency;
  final List<PaymentTransaction> transactions;
  final List<LedgerLine> ledgerEntries;

  bool get isPaid => paymentStatus.toLowerCase() == 'success';

  factory OrderPayment.fromJson(Map<String, dynamic> json) => OrderPayment(
        orderId: json['order_id'] as String,
        orderStatus: (json['order_status'] ?? '') as String,
        paymentStatus: (json['payment_status'] ?? '') as String,
        subtotalPaise: (json['subtotal_paise'] ?? 0) as int,
        deliveryFeePaise: (json['delivery_fee_paise'] ?? 0) as int,
        platformFeePaise: (json['platform_fee_paise'] ?? 0) as int,
        totalPaise: (json['total_paise'] ?? 0) as int,
        currency: (json['currency'] ?? 'INR') as String,
        transactions: (json['transactions'] as List? ?? [])
            .map((e) => PaymentTransaction.fromJson(e as Map<String, dynamic>))
            .toList(),
        ledgerEntries: (json['ledger_entries'] as List? ?? [])
            .map((e) => LedgerLine.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

/// POST /payments/transactions/{id}/confirm response.
class ConfirmResult {
  ConfirmResult({
    required this.transaction,
    required this.orderStatus,
    required this.orderPaymentStatus,
    required this.ledgerEntries,
    required this.alreadyConfirmed,
  });

  final PaymentTransaction transaction;
  final String orderStatus;
  final String orderPaymentStatus;
  final List<LedgerLine> ledgerEntries;
  final bool alreadyConfirmed;

  factory ConfirmResult.fromJson(Map<String, dynamic> json) => ConfirmResult(
        transaction: PaymentTransaction.fromJson(
          json['transaction'] as Map<String, dynamic>,
        ),
        orderStatus: (json['order_status'] ?? '') as String,
        orderPaymentStatus: (json['order_payment_status'] ?? '') as String,
        ledgerEntries: (json['ledger_entries'] as List? ?? [])
            .map((e) => LedgerLine.fromJson(e as Map<String, dynamic>))
            .toList(),
        alreadyConfirmed: (json['already_confirmed'] ?? false) as bool,
      );
}
