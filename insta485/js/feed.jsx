import React, { useState, useEffect } from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import Post from "./post";

export default function Feed() {
  const [posts, setPosts] = useState([]);
  const [nextURL, setNext] = useState();
  const [postLength, setPostsLength] = useState(0);

  // Initial Fetch
  useEffect(() => {
    fetch("/api/v1/posts/")
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        setPosts(data.results);
        setNext(data.next);
        setPostsLength(data.results.length);
      });
  }, []);

  // Next Fetch
  const getNextPosts = React.useCallback(() => {
    if (nextURL) {
      fetch(nextURL)
        .then((response) => {
          if (!response.ok) throw Error(response.statusText);
          return response.json();
        })
        .then((data) => {
          setPosts([...posts, ...data.results]);
          setNext(data.next);
          setPostsLength(posts.length);
        });
    }
  }, [nextURL, posts]);

  return (
    <div className="feed">
      <div className="nav">
        <h1>Insta485</h1>
      </div>
      <div className="posts">
        <InfiniteScroll
          dataLength={postLength}
          next={getNextPosts}
          hasMore={!!nextURL}
          loader={<h4>Loading...</h4>}
          endMessage={
            <p style={{ textAlign: "center" }}>
              <b>Yay! You have seen it all</b>
            </p>
          }
        >
          {posts.map((post) => (
            <Post url={post.url} key={post.postid} />
          ))}
        </InfiniteScroll>
      </div>
    </div>
  );
}
