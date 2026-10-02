# Culture Circle Master Checklist (the standard)

Derived from the **actual Culture Circle frontend source** (`culture_circle_web`,
Next.js app), since the live site (culturecircle.in) blocks headless rendering.
This is the reference every store gets measured against.

Source of truth:
- Home: `src/app/HomePageClient.tsx`
- Collection: `src/app/category/[slug]/CategoryViewNew.tsx`
- Product (PDP): `src/app/products/all/[slug]/ProductPageClient.tsx`
- Global: Navbar + Footer design-system components

Legend for the store audit: **Required** = core, every store should have it ·
**Recommended** = strong-to-have · **CC-extra** = Culture-Circle-specific
(marketplace aggregator features; not expected on a single-brand store).

---

## GLOBAL (every page)

| # | Element | Tier | CC source |
|---|---------|------|-----------|
| G1 | Navbar with logo | Required | Navbar |
| G2 | Search bar + search dropdown | Required | SearchBar, SearchDropdown |
| G3 | Cart (drawer / view cart button) | Required | ViewCartButton |
| G4 | Mobile hamburger menu | Required | MobileHamburgerMenu |
| G5 | Delivery-location / pincode row | Recommended | DeliveryLocationRow |
| G6 | Country / region picker | CC-extra | CountryPicker |
| G7 | Help dropdown | Recommended | HelpDropdown |
| G8 | App-download banner | CC-extra | AppDownloadBanner |
| G9 | Footer with link columns | Required | Footer, FooterColumn |
| G10 | Announcement / narrow strip | Recommended | NarrowStrip |

## HOME PAGE

| # | Element | Tier | CC source |
|---|---------|------|-----------|
| H1 | Hero banner (autoplay carousel) | Required | HomeBanner (autoPlay) |
| H2 | Drop banner / featured drop | Recommended | DropBanner, DropSection |
| H3 | Flat banners rail | Recommended | FlatBannersRail |
| H4 | Brand strip / logo wall | Recommended | BrandStriplogo |
| H5 | Tabbed category showcase | Required | TabbedCategoryShowcase |
| H6 | Category showcase (category cards) | Required | CategoryShowcase |
| H7 | Trending products | Required | TrendingHome |
| H8 | Luxury / curated showcase | Recommended | LuxuryShowcase, CultureLuxeShowcase |
| H9 | Sneaker / vertical showcase | Recommended | SneakerShowcase |
| H10 | Instant-shipping highlight | Recommended | InstantShipping |
| H11 | Social proof (Shark Tank / press) | CC-extra | SharkSection, MediaArticlesSection |
| H12 | For-Me / personalization | CC-extra | ForMeShowcase, GenderSelector |
| H13 | Looks / lookbook | Recommended | LooksShowcase |
| H14 | Assurances + product benefits | Required | AssuredClaim, ProductBenefitsHome |
| H15 | Store experience / locations | CC-extra | StoreExperience, GlobalLocationsShowcase |
| H16 | Testimonials | Recommended | Testimonial |

## COLLECTION / CATEGORY PAGE

| # | Element | Tier | CC source |
|---|---------|------|-----------|
| C1 | Breadcrumb | Required | Breadcrumb |
| C2 | Category page header / title | Required | CategoryPageHeader |
| C3 | Category banner | Recommended | EventCategoryBanner |
| C4 | Filters (active + inline strip) | Required | ActiveFilters, InlineFilterStrip |
| C5 | Sort control | Required | (within filter strip) |
| C6 | Scrollable vertical product grid | Required | CategoryProductGrid |
| C7 | Consistent product cards | Required | ProductCard |
| C8 | Sub-brand carousel | Recommended | SubBrandCarousel |
| C9 | Sold-out / fomo treatment | Recommended | SoldOutFlipCard, EventFomoToast |
| C10 | Explore-more / pagination | Required | ExploreMore |
| C11 | Category SEO content block | Recommended | CategorySEOContent |

## PRODUCT (PDP) PAGE

| # | Element | Tier | CC source |
|---|---------|------|-----------|
| P1 | Product image gallery / carousel | Required | ProductViewCarousel, ProductImage |
| P2 | Product header (title, price) | Required | ProductHeader |
| P3 | Variant / family selector | Required | ProductVariantFamily |
| P4 | Size selector | Required | ProductSizeSelector |
| P5 | Buy / Add-to-cart button | Required | ProductBuyButton |
| P6 | Delivery info + pincode check | Required | ProductDeliveryInfo |
| P7 | Assurance / authenticity badges | Required | ProductAssurance, CertificateSection |
| P8 | Spec tiles / details | Required | ProductSpecTiles, ProductDetailsFaq |
| P9 | EMI / payment options | Recommended | ProductEMIInfo |
| P10 | Seller comparison | CC-extra | ProductSellerComparison |
| P11 | Featured / related products carousel | Required | FeaturedProducts |
| P12 | Style looks / pairs-with | Recommended | StyleLooks |
| P13 | Drop note / culture note | Recommended | ProductDropNote, CultureNote |

## CART / CHECKOUT

| # | Element | Tier | CC source |
|---|---------|------|-----------|
| K1 | Cart line items with image + qty | Required | (cart drawer / page) |
| K2 | Order summary + total | Required | — |
| K3 | Checkout CTA | Required | — |
| K4 | Trust / assurance row | Recommended | — |
| K5 | Empty-cart state | Required | — |
