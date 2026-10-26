-- Published blog posts (decision D19). Only the admin can write them; every signed-in user can read them.
-- body is the post document the Blog page builds: title, sections, and the price and signal snapshot.

CREATE TABLE blog_posts (
    id            text PRIMARY KEY,
    stock         text NOT NULL,
    published_at  timestamptz NOT NULL,
    body          jsonb NOT NULL,
    author_id     bigint REFERENCES users(id) ON DELETE SET NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX blog_posts_published_idx ON blog_posts (published_at DESC);
CREATE INDEX blog_posts_stock_idx ON blog_posts (stock, published_at DESC);
