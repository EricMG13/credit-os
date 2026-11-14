// The conversation parts (mock frame "Thread panel"; behaviour list 2.9), rendered on their own.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { createRef, type RefObject } from "react";
import type { SignalComment } from "./slice";
import { Composer, MessageList } from "./parts/Messages";

const comment = (over: Partial<SignalComment> & { id: string }): SignalComment => ({
  author: { initials: "TO", name: "Tobias O" },
  own: false,
  time: "10:02",
  text: "Sharing for Thursday.",
  edited: false,
  removed: false,
  reactions: [],
  replies: [],
  ...over,
});

const reply = comment({
  id: "r1",
  author: { initials: "IK", name: "Ines K" },
  time: "10:15",
  text: "Agreed.",
  edited: true,
});
const first = comment({
  id: "c1",
  reactions: [
    { word: "Agree", count: "2", mine: true },
    { word: "Seen", count: "1", mine: false },
  ],
  replies: [reply],
});
const removed = comment({
  id: "c2",
  author: { initials: "JW", name: "Jonas W" },
  time: "10:31",
  text: null,
  removed: true,
});
const mine = comment({
  id: "c3",
  author: { initials: "ML", name: "Mara L" },
  own: true,
  time: null,
  text: "I will pull the test dates.",
});

function list(over: Partial<Parameters<typeof MessageList>[0]> = {}) {
  const onToggle = vi.fn();
  const onReply = vi.fn();
  render(
    <MessageList
      comments={[first, removed, mine]}
      onReply={onReply}
      isPressed={(c, word) => c.reactions.some((r) => r.word === word && r.mine)}
      onToggle={onToggle}
      {...over}
    />,
  );
  return { onToggle, onReply };
}

describe("the message list", () => {
  it("is an ordered list named Comments with each reply in a list under its parent", () => {
    list();
    const comments = screen.getByRole("list", { name: "Comments" });
    expect(comments.tagName).toBe("OL");
    const replies = within(comments).getByRole("list", { name: "Replies to Tobias O" });
    expect(within(replies).getByText("Agreed.")).toBeInTheDocument();
    expect(
      within(replies).getByText("Sharing for Thursday.", { selector: "blockquote" }),
    ).toBeInTheDocument();
  });

  it("draws the time, ', edited' after it, and the removed comment's sentence with no reactions or Reply", () => {
    list();
    expect(screen.getByText("10:15, edited")).toBeInTheDocument();
    expect(screen.getByText("10:02")).toBeInTheDocument();
    expect(screen.getByText("This comment was removed by its author.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Jonas W/ })).toBeNull();
    expect(screen.queryByText("Jonas W", { selector: "button *" })).toBeNull();
  });

  it("labels the viewer's own comment You, with no time when there is none", () => {
    list();
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.queryByText("Mara L")).toBeNull();
    expect(screen.getByText("I will pull the test dates.")).toBeInTheDocument();
  });

  it("draws comment text as plain text, with no HTML and no link", () => {
    list({ comments: [comment({ id: "x", text: "<b>bold</b> see https://example.com\nnext" })] });
    const bubble = screen.getByText(/bold/);
    expect(bubble.textContent).toBe("<b>bold</b> see https://example.com\nnext");
    expect(bubble.querySelector("b")).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
    expect(bubble.className).toContain("whitespace-pre-wrap");
  });

  it("names each reaction with its word, the delivered count when there is one, and the author", () => {
    list();
    const names = screen.getAllByRole("button").map((b) => b.getAttribute("aria-label"));
    expect(names).toContain("Agree, 2: comment by Tobias O");
    expect(names).toContain("Disagree: comment by Tobias O");
    expect(names).toContain("Seen, 1: comment by Tobias O");
    expect(names).toContain("Agree: comment by Ines K");
    expect(names).toContain("Seen: comment by You");
    expect(screen.getByRole("button", { name: "Disagree: comment by Tobias O" })).toHaveTextContent(
      /^Disagree$/,
    );
    expect(screen.getByRole("button", { name: "Agree, 2: comment by Tobias O" })).toHaveTextContent(
      /^Agree 2$/,
    );
  });

  it("sets aria-pressed from the page's state and reports a toggle with its comment and word", () => {
    const { onToggle } = list();
    const agree = screen.getByRole("button", { name: "Agree, 2: comment by Tobias O" });
    expect(agree).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Seen, 1: comment by Tobias O" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    fireEvent.click(agree);
    expect(onToggle).toHaveBeenCalledWith(first, "Agree");
  });

  it("draws Reply only on a top-level comment that is not removed, naming its author", () => {
    const { onReply } = list();
    const buttons = screen.getAllByRole("button", { name: /^Reply/ });
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Reply to Tobias O",
      "Reply to You",
    ]);
    fireEvent.click(buttons[0] ?? document.body);
    expect(onReply).toHaveBeenCalledWith(first);
  });

  it("draws no Reply at all when replying is not allowed", () => {
    list({ onReply: null });
    expect(screen.queryByRole("button", { name: /Reply/ })).toBeNull();
    expect(screen.getAllByRole("button", { name: /^Agree/ }).length).toBeGreaterThan(0);
  });

  it("draws a reply to a removed comment with no quote and no Reply of its own", () => {
    list({ comments: [{ ...removed, replies: [reply] }] });
    expect(screen.queryByRole("blockquote")).toBeNull();
    expect(document.querySelector("blockquote")).toBeNull();
    expect(screen.queryByRole("button", { name: /Reply/ })).toBeNull();
  });
});

function composer(over: Partial<Parameters<typeof Composer>[0]> = {}) {
  const box: RefObject<HTMLTextAreaElement | null> = createRef();
  const onSend = vi.fn();
  const onCancelReply = vi.fn();
  render(
    <Composer
      name="Mara L"
      initials="ML"
      replyingTo={null}
      onCancelReply={onCancelReply}
      onSend={onSend}
      boxRef={box}
      {...over}
    />,
  );
  const field = screen.getByRole("textbox", { name: "Write a comment" });
  return { field, onSend, onCancelReply };
}

describe("the composer", () => {
  it("has the Write a comment box, the viewer's name and a Send button", () => {
    const { field } = composer();
    expect(field).toHaveAttribute("placeholder", "Write a comment");
    expect(screen.getByText("Mara L")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled();
  });

  it("says Write something first. for an empty send, sends nothing and keeps focus in the box", () => {
    const { field, onSend } = composer();
    fireEvent.change(field, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByText("Write something first.")).toBeInTheDocument();
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(document.activeElement).toBe(field);
  });

  it("clears the message once the viewer types again", () => {
    const { field } = composer();
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    fireEvent.change(field, { target: { value: "a" } });
    expect(screen.queryByText("Write something first.")).toBeNull();
  });

  it("sends the trimmed text, clears the box and keeps focus in it", () => {
    const { field, onSend } = composer();
    fireEvent.change(field, { target: { value: "  Looks right.\nSecond line  " } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(onSend).toHaveBeenCalledExactlyOnceWith("Looks right.\nSecond line");
    expect(field).toHaveValue("");
    expect(screen.queryByText("Write something first.")).toBeNull();
    expect(document.activeElement).toBe(field);
  });

  it("shows who is being replied to with a Cancel that moves focus to the box", () => {
    const { field, onCancelReply } = composer({ replyingTo: "Tobias O" });
    expect(screen.getByText("Replying to Tobias O")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancelReply).toHaveBeenCalledOnce();
    expect(document.activeElement).toBe(field);
  });

  it("draws no Replying line for a new comment", () => {
    composer();
    expect(screen.queryByText(/Replying to/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
  });
});
