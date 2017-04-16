drop table if exists posts;
create table posts (
  id integer,
  post_id text not null primary key,
  color text not null,
  created_at text not null,
  distance integer,
  location text not null,
  message text,
  image_url text,
  image_headers text,
  pin_count integer,
  post_own text not null,
  updated_at text not null,
  user_handle text not null,
  vote_count integer
);

drop table if exists comments;
create table comments (
  id integer,
  main_post_id text not null primary key,
  post_id text not null,
  color text not null,
  created_at text not null,
  distance integer,
  location text not null,
  message text,
  image_url text,
  image_headers text,
  pin_count integer,
  post_own text not null,
  updated_at text not null,
  user_handle text not null,
  vote_count integer
);
