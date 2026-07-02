/*
 * BLE peripheral: standard Battery Service (fed by the nPM1300 measurements)
 * plus a small custom Motion service.
 *
 * Motion service (128-bit UUIDs, base 6a570000-...):
 *   6a570001  step count      uint32 LE  read + notify
 *   6a570002  activity state  uint8      read (0=idle, 1=active)
 *
 * Advertising uses slow intervals (1–2 s) — connectable but cheap: the
 * watch is the peripheral and latency matters less than idle current.
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/services/bas.h>
#include <zephyr/settings/settings.h>

#include "jrwatch.h"

LOG_MODULE_REGISTER(ble, CONFIG_LOG_DEFAULT_LEVEL);

#define JR_UUID_SVC  BT_UUID_DECLARE_128(BT_UUID_128_ENCODE( \
	0x6a570000, 0x8f9d, 0x4a7c, 0x9b31, 0x24d1c30f51aa))
#define JR_UUID_STEPS BT_UUID_DECLARE_128(BT_UUID_128_ENCODE( \
	0x6a570001, 0x8f9d, 0x4a7c, 0x9b31, 0x24d1c30f51aa))
#define JR_UUID_STATE BT_UUID_DECLARE_128(BT_UUID_128_ENCODE( \
	0x6a570002, 0x8f9d, 0x4a7c, 0x9b31, 0x24d1c30f51aa))

static bool steps_notify_enabled;

static ssize_t read_steps(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			  void *buf, uint16_t len, uint16_t offset)
{
	uint32_t v = sys_cpu_to_le32(jr_status.steps);

	return bt_gatt_attr_read(conn, attr, buf, len, offset, &v, sizeof(v));
}

static ssize_t read_state(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			  void *buf, uint16_t len, uint16_t offset)
{
	uint8_t v = (jr_status.state == JR_STATE_ACTIVE) ? 1 : 0;

	return bt_gatt_attr_read(conn, attr, buf, len, offset, &v, sizeof(v));
}

static void steps_ccc_changed(const struct bt_gatt_attr *attr, uint16_t value)
{
	steps_notify_enabled = (value == BT_GATT_CCC_NOTIFY);
}

BT_GATT_SERVICE_DEFINE(jr_svc,
	BT_GATT_PRIMARY_SERVICE(JR_UUID_SVC),
	BT_GATT_CHARACTERISTIC(JR_UUID_STEPS,
			       BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
			       BT_GATT_PERM_READ, read_steps, NULL, NULL),
	BT_GATT_CCC(steps_ccc_changed,
		    BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
	BT_GATT_CHARACTERISTIC(JR_UUID_STATE, BT_GATT_CHRC_READ,
			       BT_GATT_PERM_READ, read_state, NULL, NULL),
);

static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR),
	BT_DATA(BT_DATA_NAME_COMPLETE, CONFIG_BT_DEVICE_NAME,
		sizeof(CONFIG_BT_DEVICE_NAME) - 1),
};

/* slow advertising: 1–2 s interval keeps advertise current in the low µA */
static const struct bt_le_adv_param adv_slow = BT_LE_ADV_PARAM_INIT(
	BT_LE_ADV_OPT_CONN, 0x0640 /* 1 s */, 0x0c80 /* 2 s */, NULL);

void jr_ble_notify_steps(uint32_t steps)
{
	static uint32_t last;

	if (!steps_notify_enabled || steps == last) {
		return;
	}
	last = steps;
	uint32_t v = sys_cpu_to_le32(steps);

	(void)bt_gatt_notify(NULL, &jr_svc.attrs[1], &v, sizeof(v));
}

static void connected(struct bt_conn *conn, uint8_t err)
{
	LOG_INF("BLE connected (err %u)", err);
	k_event_post(&jr_events, JR_EVT_TICK);
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
	LOG_INF("BLE disconnected (0x%02x)", reason);
	(void)bt_le_adv_start(&adv_slow, ad, ARRAY_SIZE(ad), NULL, 0);
}

BT_CONN_CB_DEFINE(conn_cbs) = {
	.connected = connected,
	.disconnected = disconnected,
};

int jr_ble_init(void)
{
	int err = bt_enable(NULL);

	if (err) {
		LOG_ERR("bt_enable: %d", err);
		return err;
	}
	if (IS_ENABLED(CONFIG_SETTINGS)) {
		settings_load();
	}
	err = bt_le_adv_start(&adv_slow, ad, ARRAY_SIZE(ad), NULL, 0);
	if (err) {
		LOG_ERR("adv start: %d", err);
	}
	/* battery service gets its first value once power_sample runs */
	return err;
}
