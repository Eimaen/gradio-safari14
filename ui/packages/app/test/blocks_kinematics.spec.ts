import { test, expect, Page } from "@playwright/test";

function mock_demo(page: Page, demo: string) {
	return page.route("**/config", (route) => {
		return route.fulfill({
			headers: {
				"Access-Control-Allow-Origin": "*"
			},
			path: `../../../demo/${demo}/config.json`
		});
	});
}

function mock_api(page: Page, body: Array<unknown>) {
	return page.route("**/run/predict", (route) => {
		const id = JSON.parse(route.request().postData()!).fn_index;
		return route.fulfill({
			headers: {
				"Access-Control-Allow-Origin": "*"
			},
			body: JSON.stringify({
				data: body[id]
			})
		});
	});
}

test("renders the correct elements", async ({ page }) => {
	await mock_demo(page, "blocks_kinematics");
	await mock_api(page, [[25, 45]]);
	await page.goto("http://localhost:9876");

	await Promise.all([
		page.click("button:has-text('Run')"),
		page.waitForResponse("**/run/predict")
	]);
});
