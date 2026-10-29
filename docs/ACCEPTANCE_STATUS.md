# Acceptance status

Generated 2026-10-29 04:30 UTC by `scripts/acceptance_report.py`. Suite: 209/209 tests passed.

Statuses follow DECISIONS.md D-S02. `passed_domain` and `passed_simulator` are evidence about this code against fixtures and simulators; they are **not** evidence about any real provider, merchant, courier, device or operation. SIMULATED — NOT REAL MONEY.

Summary: deferred_not_in_scope: 5, passed_browser: 1, passed_domain: 40, passed_simulator: 34.

| ID | Scenario | Status | Evidence (tests) | Limitations |
|---|---|---|---|---|
| T01 | Exact item and verified mapping | `passed_domain` | test_t01_exact_item_with_verified_mapping |  |
| T02 | 2 litres vs two 2-litre bottles | `passed_domain` | test_t02_ambiguous_quantity_requires_clarification, test_t02_pack_count_is_not_a_measure |  |
| T03 | Low-confidence shelf-photo match | `passed_domain` | test_t03_suggested_match_is_not_orderable_until_user_confirms | Fabricated extraction only; real camera/OCR accuracy unproven. |
| T04 | Locked item unavailable | `passed_domain` | test_t04_locked_item_unavailable_blocks_without_substitute |  |
| T05 | Must-have fails in allow-partial basket | `passed_simulator` | test_t05_must_have_overrides_allow_partial |  |
| T06 | Optional item removed under permission | `passed_simulator` | test_immediate_permitted_omission_refunds_only_failed_leg, test_t06_permitted_omission_removes_only_that_leg |  |
| T07 | Stock observed but no hold | `passed_simulator` | test_t07_no_hold_means_no_firm_quote_and_other_holds_released |  |
| T08 | Reservation expires during 3DS | `passed_simulator` | test_t08_reservation_expires_during_3ds |  |
| T09 | Immediate payment after hold expiry | `passed_simulator` | test_t09_immediate_payment_after_expiry_refunds_when_supply_gone, test_t09_immediate_payment_after_expiry_resecures_supply |  |
| T10 | Merchant loses reserved stock | `passed_simulator` | test_t10_merchant_loses_reserved_stock |  |
| T11 | Delivery threshold changes split | `passed_domain` | test_t11_delivery_threshold_changes_optimal_split |  |
| T12 | Ineligible loyalty promotion | `passed_domain` | test_t12_loyalty_price_requires_verified_membership |  |
| T13 | VAT-inclusive price, no second VAT | `passed_domain` | test_single_store_basket_and_totals_are_vat_inclusive_t13 |  |
| T14 | Larger pack cheaper per unit | `passed_domain` | test_t14_lower_unit_price_never_exceeds_requested_quantity |  |
| T15 | Solver timeout with incumbent | `passed_domain` | test_t15_solver_budget_exhausted_returns_honest_feasible_incumbent |  |
| T16 | Cheapest misses deadline | `passed_domain` | test_t16_cheapest_basket_that_misses_deadline_is_excluded |  |
| T17 | Fastest-complete uses final leg | `passed_domain` | test_t17_fastest_complete_uses_final_leg |  |
| T18 | Approved conditions altered | `passed_domain` | test_t18_quote_cannot_change_and_mismatched_approval_rejected |  |
| T19 | Address changes behind an id | `passed_domain` | test_t19_approved_address_version_survives_later_edit |  |
| T20 | Replayed approval assertion | `passed_domain` | test_t20_replayed_assertion_rejected |  |
| T21 | Wrong origin/account/credential | `passed_domain` | test_t21_wrong_origin_account_or_credential_rejected |  |
| T22 | PIN-capable device, no Face ID | `passed_browser` | test_approval_page_with_virtual_passkey, test_t22_user_verification_required_but_not_biometric | Virtual authenticator only; a physical PIN-only device is manual_pending. |
| T23 | Recycled phone number recovery | `passed_domain` | test_t23_no_phone_based_recovery_route | Negative boundary only: no phone-based recovery exists. Full recovery journey not built. |
| T24 | Parallel orders from one approval | `passed_domain` | test_t24_parallel_orders_from_one_approval_execute_once |  |
| T25 | Same key, changed payload | `passed_domain` | test_t25_concurrent_same_key_has_one_effect, test_t25_same_key_changed_payload_conflicts, test_t25_same_key_same_request_replays |  |
| T26 | Provider accepted, response lost | `passed_simulator` | test_t26_timeouts_after_provider_accepted_never_duplicate |  |
| T27 | Unknown beyond provider horizon | `passed_simulator` | test_t27_unknown_beyond_horizon_blocks_automatic_resend |  |
| T28 | Duplicate/out-of-order webhook | `passed_simulator` | test_t28_duplicate_webhook_has_one_effect, test_t28_duplicate_webhook_is_idempotent |  |
| T29 | Invalid webhook signature | `passed_domain` | test_t29_invalid_signature_rejected_without_state_change, test_t29_webhook_with_bad_signature_is_rejected_over_http |  |
| T30 | Callback vs lookup conflict | `passed_simulator` | test_t30_callback_success_but_lookup_conflicts |  |
| T31 | Two destinations, single-destination product | `passed_simulator` | test_t31_single_destination_profile_rejects_before_any_call | Simulated profiles; real provider capabilities are provider_pending (D02). |
| T32 | Retailer-specific refund on proportional split | `passed_simulator` | test_t32_retailer_specific_refund_on_proportional_split | Simulated allocation; real provider behaviour provider_pending. |
| T33 | Partial refunds race | `passed_simulator` | test_t33_concurrent_partial_refunds_cannot_exceed_entitlement |  |
| T34 | Refund timeout then user retry | `passed_simulator` | test_t34_refund_timeout_then_user_retry_is_the_same_refund |  |
| T35 | Refund and chargeback overlap | `passed_simulator` | test_t35_chargeback_after_refund_flags_double_recovery, test_t35_refund_during_open_chargeback_is_held | Detection and hold only; dispute evidence workflow is operational. |
| T36 | Merchant payout fails | `passed_simulator` | test_t53_t36_t54_settlement_import |  |
| T37 | Full basket fails before capture | `passed_simulator` | test_t37_basket_fails_before_capture_voids_and_releases |  |
| T38 | One leg fails after another commits | `passed_simulator` | test_t38_immediate_one_leg_fails_after_other_committed |  |
| T39 | Cancellation races capture | `passed_simulator` | test_cancel_during_checkout_waits_for_observed_result, test_t39_cancellation_races_capture |  |
| T40 | Courier booking times out | `passed_simulator` | test_t40_booking_unknown_is_resolved_by_the_sweep, test_t40_courier_booking_timeout_looks_up_not_rebooks |  |
| T41 | Consolidated pickup, second store late | `deferred_not_in_scope` | — | Consolidation is disabled (D-S03.1); every leg is delivered separately. |
| T42 | Delivery to unapproved address | `passed_simulator` | test_t42_delivery_to_unapproved_address_rejected |  |
| T43 | Missing/damaged package | `passed_simulator` | test_t43_damaged_item_issue_becomes_targeted_refund | Targeted refund only; evidence handling and liability are operational. |
| T44 | Product recall | `passed_domain` | test_t44_recall_identifies_affected_orders | Identification of affected orders only; response workflow manual_pending. |
| T45 | Malicious merchant description | `passed_domain` | test_t45_malicious_merchant_text_changes_nothing |  |
| T46 | Malicious URL in product/media | `passed_domain` | test_t46_application_code_has_no_arbitrary_fetch_capability | No fetch capability exists in app code; production egress policy is an environment requirement. |
| T47 | Model claims payment without evidence | `passed_domain` | test_t47_agent_cannot_inject_status_price_or_payee |  |
| T48 | Model poisons stored preference | `passed_domain` | test_t48_agent_preference_is_not_promoted_without_owner | Fixture agent; robustness of a real model unproven. |
| T49 | Another account's UUID | `passed_domain` | test_t49_address_of_another_account_is_not_found, test_t49_other_account_cannot_see_or_approve_quote, test_t49_other_accounts_ids_are_not_found |  |
| T50 | Restore after outbox commit | `passed_simulator` | test_t50_restore_after_outbox_commit_before_dispatch |  |
| T51 | Restore after provider accepted | `passed_simulator` | test_t51_crash_after_provider_accepted_before_local_write |  |
| T52 | Unbalanced ledger posting | `passed_domain` | test_database_rejects_unbalanced_transaction_at_commit, test_t52_unbalanced_posting_rejected_paused_and_alerted |  |
| T53 | Settlement report imported twice | `passed_simulator` | test_t53_t36_t54_settlement_import |  |
| T54 | Unexplained discrepancy | `passed_simulator` | test_t54_unexplained_difference_is_an_owned_case_not_an_entry |  |
| T55 | WhatsApp unavailable | `deferred_not_in_scope` | — | No WhatsApp channel in this sprint; web status/receipts are the only channel. |
| T56 | ID/card details in chat | `deferred_not_in_scope` | test_redaction_of_card_and_id_numbers, test_redaction_preserves_identifiers_and_hashes | No chat channel. Log/audit redaction is tested; the chat handling path is not built. |
| T57 | Non-converting sessions cost | `deferred_not_in_scope` | — | Cost instrumentation (cost_events) not built this sprint. |
| T58 | Low reserve or support overload | `passed_domain` | test_kill_switch_does_not_block_ledger_postings, test_t58_paused_money_path_blocks_new_orders_but_not_status | Kill switch limits new exposure; reserve and support-load measurement not built. |
| T59 | Language-specific extraction fails | `deferred_not_in_scope` | test_t02_ambiguous_quantity_requires_clarification | No language model. Ambiguous items already block quoting until clarified. |
| T60 | List exceeds ambient pilot coverage | `passed_domain` | test_t60_unsupported_items_are_disclosed_not_hidden |  |
| W01 | Duplicate confirmed top-up | `passed_simulator` | test_w01_duplicate_confirmed_topup_credits_once |  |
| W02 | Top-up pending/failed/unverified | `passed_simulator` | test_w02_pending_or_failed_topup_is_not_spendable |  |
| W03 | Wrong currency/destination/reference | `passed_simulator` | test_w03_mismatched_topup_goes_to_suspense_or_quarantine |  |
| W04 | Concurrent allocation | `passed_domain` | test_w04_concurrent_allocation_never_exceeds_owner_funds |  |
| W05 | Concurrent spend on one envelope (A3) | `passed_domain` | test_w05a_two_concurrent_reservations_cannot_overspend_one_envelope, test_w05b_w14_reserve_racing_owner_withdrawal, test_w05c_separate_envelopes_are_isolated |  |
| W06 | Funds without grant/approval | `passed_domain` | test_w06_funds_without_authority_is_refused |  |
| W07 | Grant without funds | `passed_domain` | test_w07_authority_without_funds_is_refused, test_w07_funds_spent_after_quote_refused_at_reservation |  |
| W08 | Agent broadens scope / redirects | `passed_domain` | test_w08_agent_cannot_widen_its_own_authority |  |
| W09 | Revoked between request and commitment | `passed_simulator` | test_w09_revocation_between_request_and_commitment_stops |  |
| W10 | Cancellation after uncertain merchant action | `passed_simulator` | test_w10_no_release_while_merchant_state_is_uncertain |  |
| W11 | Reservation release delivered twice | `passed_domain` | test_w11_release_delivered_twice_restores_once |  |
| W12 | Partial refunds race or repeat | `passed_domain` | test_w12_partial_refunds_never_exceed_entitlement |  |
| W13 | Confirmed top-up later reversed | `passed_simulator` | test_w13_confirmed_topup_later_reversed |  |
| W14 | Redemption races purchase | `passed_domain` | test_w05b_w14_reserve_racing_owner_withdrawal |  |
| W15 | Small orders evade per-order cap | `passed_domain` | test_w15_small_orders_cannot_evade_aggregate_caps |  |
| W16 | Wallet purchase, no external debit | `passed_simulator` | test_w16_wallet_purchase_has_no_external_debit |  |
| W17 | Operating vs customer funds | `passed_domain` | test_w17_customer_funds_and_operating_reserve_are_separate |  |
| W18 | Refund near period boundary | `passed_domain` | test_w18_refund_restores_money_not_authority |  |
| W19 | Crash after external result | `passed_simulator` | test_w19_crash_after_merchant_accepted_before_local_record |  |
| W20 | Synthetic DB under live config | `passed_domain` | test_w20_synthetic_database_refused_under_live_runtime |  |
