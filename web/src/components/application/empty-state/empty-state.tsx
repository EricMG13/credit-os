import type { ComponentPropsWithRef } from "react";
import { SearchLg } from "@untitledui/icons";
import { FeaturedIcon as FeaturedIconbase } from "@/components/foundations/featured-icon/featured-icon";
import { cx } from "@/utils/cx";

const Root = (props: ComponentPropsWithRef<"div">) => {
  return (
    <div
      {...props}
      className={cx(
        "mx-auto flex w-full max-w-lg flex-col items-center justify-center",
        props.className,
      )}
    />
  );
};

const FeaturedIcon = ({
  color = "gray",
  icon = SearchLg,
  ...props
}: Partial<ComponentPropsWithRef<typeof FeaturedIconbase>>) => {
  return <FeaturedIconbase {...props} {...{ color, icon }} size="xl" />;
};

const Header = (props: ComponentPropsWithRef<"header">) => {
  return <header {...props} className={cx("relative mb-5", props.className)} />;
};

const Content = (props: ComponentPropsWithRef<"div">) => {
  return (
    <main
      {...props}
      className={cx(
        "z-10 mb-8 flex w-full max-w-88 flex-col items-center justify-center gap-2",
        props.className,
      )}
    />
  );
};

const Footer = (props: ComponentPropsWithRef<"div">) => {
  return <footer {...props} className={cx("z-10 flex gap-3", props.className)} />;
};

interface TitleProps extends ComponentPropsWithRef<"h2"> {
  /** The page's own empty state is an h2 under its h1; one shown under a section's h2 (the kit) is an h3. */
  as?: "h2" | "h3";
}

const Title = ({ as: Heading = "h2", ...props }: TitleProps) => {
  return (
    <Heading {...props} className={cx("text-xl font-semibold text-primary", props.className)} />
  );
};

const Description = (props: ComponentPropsWithRef<"p">) => {
  return <p {...props} className={cx("text-center text-md text-tertiary", props.className)} />;
};

const EmptyState = Root as typeof Root & {
  Title: typeof Title;
  Header: typeof Header;
  Footer: typeof Footer;
  Content: typeof Content;
  Description: typeof Description;
  FeaturedIcon: typeof FeaturedIcon;
};

EmptyState.Title = Title;
EmptyState.Header = Header;
EmptyState.Footer = Footer;
EmptyState.Content = Content;
EmptyState.Description = Description;
EmptyState.FeaturedIcon = FeaturedIcon;

export { EmptyState };
