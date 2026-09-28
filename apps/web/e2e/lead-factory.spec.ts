import { expect, test } from "@playwright/test";

test("operator can inspect and approve a demo lead", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Lead operations overview" })).toBeVisible();
  await expect(page.getByText("3", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "Accounts" }).click();
  await expect(page.getByText("[Demo] SkyMeal Airline Catering")).toBeVisible();
  await page.getByRole("link", { name: "[Demo] SkyMeal Airline Catering" }).click();

  await expect(page.getByText("ICP fit")).toBeVisible();
  await expect(page.getByText("Airline meal boxes")).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByRole("status")).toContainText("Review saved");
  await expect(page.getByText("Approved", { exact: true }).first()).toBeVisible();
});
