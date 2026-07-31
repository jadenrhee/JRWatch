/*
 * nPM1300 power management.
 *
 * - charger/fuel data via the npm1300_charger sensor channels
 * - battery % from an OCV table (LiPo, rest-ish voltage). Nordic's nRF
 *   Fuel Gauge library is the higher-accuracy NCS option; the OCV estimate
 *   keeps this app vanilla-Zephyr buildable (documented in README).
 * - VDD_IMU load-switch gating
 * - BUCK1 is held off at boot (D-012: populated 1.8 V experiment rail)
 * - ship mode: quiescent battery disconnect, wake via SW1 (SHPHLD) or USB
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/drivers/sensor/npm1300_charger.h>
#include <zephyr/drivers/mfd/npm1300.h>
#include <zephyr/drivers/regulator.h>
#include <zephyr/bluetooth/services/bas.h>

#include "jrwatch.h"

LOG_MODULE_REGISTER(power, CONFIG_LOG_DEFAULT_LEVEL);

static const struct device *const charger =
	DEVICE_DT_GET(DT_NODELABEL(npm1300_charger));
static const struct device *const pmic =
	DEVICE_DT_GET(DT_NODELABEL(npm1300));
static const struct device *const buck1 =
	DEVICE_DT_GET(DT_NODELABEL(npm1300_buck1));
static const struct device *const lsw_imu =
	DEVICE_DT_GET(DT_NODELABEL(npm1300_lsw_imu));
static const struct device *const regulators =
	DEVICE_DT_GET(DT_NODELABEL(npm1300_regulators));

/* LiPo OCV -> % (coarse 10-point table, rest voltage) */
static const struct { int16_t mv; uint8_t pct; } ocv[] = {
	{ 4180, 100 }, { 4060, 90 }, { 3980, 80 }, { 3890, 70 },
	{ 3820, 60 },  { 3770, 50 }, { 3740, 40 }, { 3700, 30 },
	{ 3650, 20 },  { 3550, 10 }, { 3300, 0 },
};

static uint8_t soc_from_mv(int32_t mv)
{
	if (mv >= ocv[0].mv) {
		return 100;
	}
	for (size_t i = 1; i < ARRAY_SIZE(ocv); i++) {
		if (mv >= ocv[i].mv) {
			int span_mv = ocv[i - 1].mv - ocv[i].mv;
			int span_pc = ocv[i - 1].pct - ocv[i].pct;

			return ocv[i].pct +
			       (mv - ocv[i].mv) * span_pc / span_mv;
		}
	}
	return 0;
}

int jr_power_init(void)
{
	if (!device_is_ready(charger) || !device_is_ready(pmic)) {
		LOG_ERR("PMIC not ready");
		return -ENODEV;
	}
	/* D-012: BUCK1 populated per the reference circuit but held OFF for
	 * the production power numbers (devicetree already boots it off;
	 * this is the belt to that suspender). */
	if (device_is_ready(buck1) && regulator_is_enabled(buck1)) {
		(void)regulator_disable(buck1);
	}
	jr_power_sample();
	return 0;
}

void jr_power_imu_rail(bool on)
{
	if (!device_is_ready(lsw_imu)) {
		return;
	}
	int err = on ? regulator_enable(lsw_imu) : regulator_disable(lsw_imu);

	if (err && err != -EALREADY) {
		LOG_WRN("VDD_IMU %d: %d", on, err);
	}
}

void jr_power_sample(void)
{
	struct sensor_value v;

	if (sensor_sample_fetch(charger)) {
		return;
	}
	if (sensor_channel_get(charger, SENSOR_CHAN_GAUGE_VOLTAGE, &v) == 0) {
		jr_status.vbat_mv = sensor_value_to_milli(&v);
		jr_status.battery_pct = soc_from_mv(jr_status.vbat_mv);
	}
	if (sensor_channel_get(charger,
			       (enum sensor_channel)SENSOR_CHAN_NPM1300_CHARGER_STATUS,
			       &v) == 0) {
		/* any charging phase counts as charging: TRICKLE (bit 2),
		 * CC (bit 3), CV (bit 4) — COMPLETED (bit 1) is not charging */
		jr_status.charging = (v.val1 & 0x1C) != 0;
	}
	(void)bt_bas_set_battery_level(jr_status.battery_pct);
}

void jr_power_ship_mode(void)
{
	struct sensor_value v;
	int err;

	/* PS: TASKENTERSHIPMODE must not be written while VBUS is present
	 * (the request could latch and fire on unplug). Live register
	 * check; refuse locally without issuing the task. */
	err = sensor_attr_get(charger,
			      (enum sensor_channel)SENSOR_CHAN_NPM1300_CHARGER_VBUS_STATUS,
			      (enum sensor_attribute)SENSOR_ATTR_NPM1300_CHARGER_VBUS_PRESENT,
			      &v);
	if (err != 0 || v.val1 != 0) {
		LOG_WRN("ship mode refused: on USB power (err %d)", err);
		return;
	}

	LOG_INF("entering ship mode");
	/* Blank the panel so ship doesn't freeze a stale face on it. The
	 * IMU rail stays up: on success the PMIC disconnects VBAT and it
	 * dies with everything else; on failure the BMI270 keeps its
	 * loaded config (a power cycle would lose it with no re-init
	 * path). */
	(void)jr_ui_display_power(false);
	k_msleep(10);
	/* TASKENTERSHIPMODE via the regulator parent — true ship mode
	 * (IQSHIP), not hibernate's wake-timer variant. Exit: SW1 (SHPHLD
	 * low >= 96 ms) or VBUS. With VBUS absent, entry is immediate —
	 * on success this does not return. */
	err = regulator_parent_ship_mode(regulators);
	k_msleep(100);
	/* still running: entry failed (bus error?) — recover the face */
	LOG_WRN("ship mode failed (err %d)", err);
	(void)jr_ui_display_power(true);
}
