"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import axios from "axios";

export default function Home() {
  const [url, setUrl] = useState("");
  const [jobs, setJobs] = useState<any[]>([]);
  const [crawlerOptions, setCrawlerOptions] = useState<any>({});
  const [pageOptions, setPageOptions] = useState<any>({});

  const startCrawl = async () => {
    try {
      const response = await axios.post("/api/crawl", { 
        url, 
        options: { 
          crawlerOptions,
          pageOptions,
        } 
      });
      const jobId = response.data.jobId || response.data.id;
      setJobs([...jobs, { id: jobId, status: "pending", url }]);
      setUrl(""); // Clear input after successful submission
    } catch (error: any) {
      console.error("Failed to start crawl:", error);
      alert(`Failed to start crawl: ${error.response?.data?.error || error.message}`);
    }
  };

  useEffect(() => {
    if (jobs.length === 0) return;

    const interval = setInterval(async () => {
      const updates = await Promise.all(
        jobs.map(async (job) => {
          if (job.status === "pending" || job.status === "scraping") {
            try {
              const response = await axios.get(`/api/crawl/status/${job.id}`);
              return { ...job, status: response.data.status };
            } catch (error) {
              console.error(`Failed to get status for ${job.id}:`, error);
              return job;
            }
          }
          return job;
        })
      );
      setJobs(updates);
    }, 5000);

    return () => clearInterval(interval);
  }, [jobs]);

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Firecrawl Frontend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex w-full items-center space-x-2">
            <Input
              type="url"
              placeholder="Enter URL to crawl"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline">Advanced Options</Button>
              </PopoverTrigger>
              <PopoverContent className="w-80">
                <Tabs defaultValue="crawler">
                  <TabsList>
                    <TabsTrigger value="crawler">Crawler</TabsTrigger>
                    <TabsTrigger value="page">Page</TabsTrigger>
                  </TabsList>
                  <TabsContent value="crawler">
                    <div className="grid gap-4">
                      <div className="space-y-2">
                        <h4 className="font-medium leading-none">Crawler Options</h4>
                        <p className="text-sm text-muted-foreground">
                          Configure the crawler behavior.
                        </p>
                      </div>
                      <div className="grid gap-2">
                        <div className="grid grid-cols-3 items-center gap-4">
                          <Label htmlFor="includes">Includes</Label>
                          <Textarea
                            id="includes"
                            placeholder="Enter patterns to include, one per line"
                            className="col-span-2 h-24"
                            onChange={(e) => setCrawlerOptions({ ...crawlerOptions, includes: e.target.value.split("\n") })}
                          />
                        </div>
                        <div className="grid grid-cols-3 items-center gap-4">
                          <Label htmlFor="excludes">Excludes</Label>
                          <Textarea
                            id="excludes"
                            placeholder="Enter patterns to exclude, one per line"
                            className="col-span-2 h-24"
                            onChange={(e) => setCrawlerOptions({ ...crawlerOptions, excludes: e.target.value.split("\n") })}
                          />
                        </div>
                        <div className="grid grid-cols-3 items-center gap-4">
                          <Label htmlFor="maxDepth">Max Depth</Label>
                          <Input
                            id="maxDepth"
                            type="number"
                            defaultValue={10}
                            className="col-span-2 h-8"
                            onChange={(e) => setCrawlerOptions({ ...crawlerOptions, maxDepth: parseInt(e.target.value) })}
                          />
                        </div>
                        <div className="grid grid-cols-3 items-center gap-4">
                          <Label htmlFor="maxPages">Max Pages</Label>
                          <Input
                            id="maxPages"
                            type="number"
                            defaultValue={0}
                            className="col-span-2 h-8"
                            onChange={(e) => setCrawlerOptions({ ...crawlerOptions, maxPages: parseInt(e.target.value) })}
                          />
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                  <TabsContent value="page">
                    <div className="grid gap-4">
                        <div className="space-y-2">
                            <h4 className="font-medium leading-none">Page Options</h4>
                            <p className="text-sm text-muted-foreground">
                            Configure the page options.
                            </p>
                        </div>
                        <div className="grid gap-2">
                            <div className="grid grid-cols-3 items-center gap-4">
                                <Label htmlFor="screenshot">Screenshot</Label>
                                <Switch
                                    id="screenshot"
                                    onCheckedChange={(checked) => setPageOptions({ ...pageOptions, screenshot: checked })}
                                />
                            </div>
                        </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </PopoverContent>
            </Popover>
            <Button onClick={startCrawl}>Crawl</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Crawl Jobs</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job ID</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell>{job.id}</TableCell>
                  <TableCell>{job.status}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
